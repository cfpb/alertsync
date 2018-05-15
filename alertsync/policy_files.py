import yaml


def parse(yaml_policy):
    document = yaml.load(yaml_policy)
    policy = {}
    conditions = {}

    for key, value in document.items():
        if key in ['name', 'incident_preference']:
            policy[key] = value
        else:
            conditions[key] = value

    return policy, conditions


def build_document(policy, conditions):
    document = {'name': policy['name'],
                'incident_preference': policy['incident_preference']}

    document.update(conditions)
    return document