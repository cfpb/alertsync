import os
import requests
import json

from collections import namedtuple
from urllib.parse import urljoin
from multidict import MultiDict


class APIRequestFailure(Exception):
    pass


class ApiWrapper(object):
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {'X-Api-Key': os.environ.get('NR_API_KEY')})

    def __getattr__(self, attr):
        method = getattr(self.session, attr)

        def do_api_call(*args, **kwargs):
            response = method(*args, **kwargs)
            if response.status_code >= 300:
                print(json.dumps(kwargs['json']) )
                raise APIRequestFailure("(%s) %s %s" % (
                    attr, args[0], response.text))
            return response

        return do_api_call


api = ApiWrapper()

ConditionChange = namedtuple('ConditionChange', ['current', 'new'])


class NewRelicAPIError(Exception):
    pass


class TooManyPolicyMatches(Exception):
    pass


class NoSuchPolicyID(Exception):
    pass


class NoSuchPolicyName(Exception):
    pass


class ConditionType(object):
    name = 'condition'
    site = 'https://api.newrelic.com/v2/'

    @property
    def dict_key(self):
        return self.name

    @property
    def collection_dict_key(self):
        return self.plural

    @property
    def plural(self):
        return self.name + 's'

    def url(self, template, **kwargs):
        kwargs['plural'] = self.plural
        path = template.format(**kwargs)
        return urljoin(self.site, path)

    def update_url(self, condition_id):
        return self.url(
            'alerts_{plural}/{condition_id}.json',
            condition_id=condition_id)

    def list_url(self, policy_id=None):
        # policy_id is here for consistency sake
        return self.url('alerts_{plural}.json')

    def singleton_url(self, condition_id):
        return self.url('alerts_{plural}/{condition_id}.json',
                        condition_id=condition_id)

    def create_url(self, policy_id):
        return self.url(
            'alerts_{plural}/policies/{policy_id}.json',
            policy_id=policy_id)

    def list(self, policy_id):
        result = api.get(self.list_url(),
                         data={'policy_id': policy_id}).json()
        return list(reversed(result[self.plural]))

    def create(self, policy_id, condition):
        details = {self.dict_key: condition}
        # condition['policy_id'] = policy_id
        if 'policy_id' in condition:
            del condition['policy_id']
        return api.post(self.create_url(policy_id),
                        json=details).json()

    def update(self, condition_id, condition):
        url = self.singleton_url(condition_id)
        details = {self.dict_key: condition}
        api.put(url, json=details)

    def delete(self, condition_id):
        url = self.singleton_url(condition_id)
        api.delete(url)


class ExternalServiceConditionType(ConditionType):
    name = 'external_service_condition'


class SyntheticsConditionType(ConditionType):
    name = 'synthetics_condition'


class PluginsConditionType(ConditionType):
    name = 'plugins_condition'


class NRQLConditionType(ConditionType):
    name = 'nrql_condition'


class InfrastructureConditionType(ConditionType):
    name = 'infrastructure_condition'
    site = 'https://infra-api.newrelic.com/v2/'

    @property
    def dict_key(self):
        return 'data'

    @property
    def collection_dict_key(self):
        return self.dict_key

    def singleton_url(self, condition_id):
        return self.url('alerts/conditions/{condition_id}',
                        condition_id=condition_id)

    def list_url(self, policy_id):
        return self.url(
            'alerts/conditions?policy_id={policy_id}',
            policy_id=policy_id)

    def create_url(self, policy_id):
        return urljoin(self.site, 'alerts/conditions')

    def list(self, policy_id):
        return api.get(self.list_url(
            policy_id=policy_id),
        ).json()[self.dict_key]

    def create(self, policy_id, condition):
        condition['policy_id'] = policy_id
        return super(
            InfrastructureConditionType, self).create(policy_id, condition)


condition_types = [
    ConditionType(),
    ExternalServiceConditionType(),
    SyntheticsConditionType(),
    PluginsConditionType(),
    NRQLConditionType(),
    InfrastructureConditionType()
]


def policy_iter():
    url = 'https://api.newrelic.com/v2/alerts_policies.json?page=%s'
    index = 1
    while True:
        policies = api.get(url % index).json()['policies']
        if len(policies) > 0:
            for policy in policies:
                yield policy
            index += 1
        else:
            break


def get_policy(policy_id):
    for policy in policy_iter():
        if policy['id'] == policy_id:
            return policy
    raise NoSuchPolicyID


def find_policy(name):
    url = 'https://api.newrelic.com/v2/alerts_policies.json'
    response = api.get(url, data={'filter[name]': name})
    exact_matches = [p for p in response.json()['policies']
                     if p['name'] == name]
    if len(exact_matches) > 1:
        raise TooManyPolicyMatches
    elif len(exact_matches) == 1:
        return exact_matches[0]
    else:
        raise NoSuchPolicyName


def create_policy(name, incident_preference):
    create_url = 'https://api.newrelic.com/v2/alerts_policies.json'
    details = {'policy': {'name': name,
                          'incident_preference': incident_preference}}
    result = api.post(create_url, json=details)
    details['policy']['id'] = result.json()['policy']['id']
    return details['policy']


def conditions_for_policy(policy_id):
    conditions = {}
    for condition_type in condition_types:
        results = condition_type.list(policy_id=policy_id)
        if results:
            conditions[condition_type.plural] = results
    return conditions


def compare_updated_conditions(policy_id, condition_type, updated_conditions):

    current_conditions = condition_type.list(policy_id)

    if not (current_conditions or updated_conditions):
        return list()   # nothing to do if both lists are empty

    current_lookup = {c['id']: c for c in current_conditions}
    lookup_by_name = MultiDict(((c['name'], c) for c in current_conditions))

    def fix_condition_id(condition):
        if 'id' in condition:
            if condition['id'] not in current_lookup.keys():
                del condition['id']

        if 'id' not in condition and condition['name'] in lookup_by_name:
            found = lookup_by_name.popone(condition['name'])
            condition['id'] = found['id']

        return condition
    updated_conditions = map(fix_condition_id, updated_conditions)

    seen_condition_ids = []
    for condition in updated_conditions:
        if 'policy_id' in condition:
            del condition['policy_id']
        if 'id' not in condition:
            yield ConditionChange(current=None,
                                  new=condition)  # no existing match
        else:
            seen_condition_ids.append(condition['id'])
            yield ConditionChange(
                current=current_lookup[condition['id']],
                new=condition)
    for condition in current_conditions:
        if condition['id'] not in seen_condition_ids:
            # no "partner" in the new conditions, so delete it
            yield ConditionChange(current=condition,
                                  new=None)


def update_conditions(policy_id, new_conditions):
    for condition_type in condition_types:
        for change in compare_updated_conditions(
                policy_id,
                condition_type,
                new_conditions.get(condition_type.plural, []),
        ):
            if change.current and not change.new:
                condition_type.delete(change.current['id'])
            elif change.new and not change.current:
                condition_type.create(policy_id, change.new)
            else:
                condition_type.update(change.current['id'], change.new)


def update_policy_details(policy_id, name, incident_preference):
    url = "https://api.newrelic.com/v2/alerts_policies/%s.json" % policy_id
    details = {'policy': {'name': name,
                          'incident_preference': incident_preference}}
    api.put(url, json=details)
    details['id'] = policy_id
    return details


def create_or_update_policy(name, incident_preference, policy_id=None):
    if policy_id:
        return update_policy_details(policy_id, name, incident_preference)
    else:
        try:
            found_policy = find_policy(name)
            return update_policy_details(found_policy['id'],
                                         name, incident_preference)

        except NoSuchPolicyName:
            return create_policy(name, incident_preference)
