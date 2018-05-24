import os
import requests

from collections import namedtuple
from urllib.parse import urljoin

session = requests.Session()
session.headers.update({'X-Api-Key': os.environ['NR_API_KEY']})


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

    def list_url(self):
        return self.url('alerts_{plural}.json')

    def create_url(self, policy_id):
        return self.url(
            'alerts_{plural}/policies/{policy_id}.json',
            policy_id=policy_id)

    def list(self, policy_id):
        return session.get(url, data={'policy_id': policy_id}).json()

    def create(self, policy_id, policy):
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


condition_types = [
    ConditionType(),
    ExternalServiceConditionType(),
    SyntheticsConditionType(),
    PluginsConditionType(),
    NRQLConditionType(),
    InfraStructureConditionType()
]


def policy_iter():
    url = 'https://api.newrelic.com/v2/alerts_policies.json?page=%s'
    index = 1
    while True:
        policies = session.get(url % index).json()['policies']
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
    response = session.get(url, data={'filter[name]': name})
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
    result = session.post(create_url, json=details)
    details['policy']['id'] = result.json()['policy']['id']
    return details['policy']


def conditions_for_policy(policy_id):
    conditions = {}
    for condition_type in condition_types:
        results = get_conditions(policy_id, condition_type)
        if 'data' in results:  # an infrastructure result
            conditions[condition_type + 's'] = results['data']
        elif results[condition_type + 's']:
            conditions.update(results)
    return conditions


def create_condition(policy_id, condition_type, condition):
    if condition_type == 'infrastructure_condition':
        url = "https://infra-api.newrelic.com/v2/alerts/conditions"
        condition['policy_id'] - policy_id
        details = {'data': condition}
    else:
        url = CREATE_CONDITION_TEMPLATE.format(policy_id=policy_id,
                                               condition_type=condition_type)
        if 'id' in condition:
            del condition['id']

        details = {condition_type: condition}
    session.post(url, json=details)


def compare_updated_conditions(policy_id, condition_type, updated_conditions):
    if condition_type == 'infrastructure_conditions':
        key = 'data'
    else:
        key = condition_type

    search_result = get_conditions(
            policy_id,
            condition_type)

    current_conditions = search_result[key]

    if not (current_conditions or updated_conditions):
        return list()   # nothing to do if both lists are empty

    current_lookup = {c['id']: c for c in current_conditions}
    lookup_by_name = {c['name']: c for c in current_conditions}

    def fix_condition_id(condition):
        if 'id' in condition:
            if condition['id'] in current_lookup.keys():
                return condition
            else:
                del condition['id']

        if condition['name'] in lookup_by_name:
            condition['id'] = lookup_by_name[condition['name']]['id']

        return condition
    updated_conditions = map(fix_condition_id, updated_conditions)
    seen_condition_ids = []
    for condition in updated_conditions:
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
        condition_type_plural = condition_type + 's'
        for change in compare_updated_conditions(
                policy_id,
                condition_type_plural,
                new_conditions.get(condition_type_plural, []),
                ):
            if change.current and not change.new:
                delete_condition(change.current['id'], condition_type)
            if change.new and not change.current:
                create_condition(policy_id, condition_type, condition)



def get_conditions(policy_id, condition_type):
    return condition_type.list(policy_id=policy_id)


def update_condition(condition, condition_type):
    if condition_type == 'infrastructure_condition':
        template = 'https://infra-api.newrelic.com/v2/alerts/conditions/{id}' # noqa
        url = template.format(condition)
    else:
        url = DELETE_CONDITION_TEMPLATE.format(condition_type=condition_type,
                                               condition_id=condition_id)
    session.delete(url)


def delete_condition(condition_id, condition_type):
    if condition_type == 'infrastructure_condition':
        template = 'https://infra-api.newrelic.com/v2/alerts/conditions/{condition_id}' # noqa
        url = template.format(condition_id=condition_id)
    else:
        url = DELETE_CONDITION_TEMPLATE.format(condition_type=condition_type,
                                               condition_id=condition_id)
    session.delete(url)


def delete_all_conditions(policy_id):
    conditions = conditions_for_policy(policy_id)
    for plural_type, conditions in conditions.items():
        condition_type = plural_type[:-1]
        for condition in conditions:
            delete_condition(policy_id, condition['id'], condition_type)


def update_policy_conditions(policy_id, conditions):
    pass


def update_policy_details(policy_id, name, incident_preference):
    url = "https://api.newrelic.com/v2/alerts_policies/%s.json" % policy_id
    details = {'policy': {'name': name,
                          'incident_preference': incident_preference}}
    session.put(url, json=details)
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
