import os
import requests

session = requests.Session()
session.headers.update({'X-Api-Key': os.environ['NR_API_KEY']})


class NewRelicAPIError(Exception):
    pass


class TooManyPolicyMatches(Exception):
    pass


class NoSuchPolicyID(Exception):
    pass


class NoSuchPolicyName(Exception):
    pass

CREATE_CONDITION_TEMPLATE = 'https://api.newrelic.com/v2/alerts_{condition_type}s/policies/{policy_id}.json' # noqa
LIST_CONDITION_TEMPLATE = 'https://api.newrelic.com/v2/alerts_{condition_type}s.json' # noqa
DELETE_CONDITION_TEMPLATE = 'https://api.newrelic.com/v2/alerts_{condition_type}s/{condition_id}.json' # noqa

condition_types = [
    'condition',
    'external_service_condition',
    'synthetics_condition',
    'plugins_condition',
    'nrql_condition'
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
        if results[condition_type + 's']:
            conditions.update(results)
    return conditions


def create_condition(policy_id, condition_type, condition):
    url = CREATE_CONDITION_TEMPLATE.format(policy_id=policy_id,
                                           condition_type=condition_type)
    if 'id' in condition:
        del condition['id']

    details = {condition_type: condition}
    session.post(url, json=details)


def create_conditions(policy_id, new_conditions):
    for plural_type, conditions in new_conditions.items():
        condition_type = plural_type[:-1]
        for condition in conditions:
            create_condition(policy_id, condition_type, condition)


def get_conditions(policy_id, condition_type):
    url = LIST_CONDITION_TEMPLATE.format(condition_type=condition_type)
    return session.get(url, data={'policy_id': policy_id}).json()


def delete_condition(policy_id, condition_id, condition_type):
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
