import sys
import yaml
import jinja2


class DuplicateValueException(Exception):
    pass


def assert_field_unique(iterable, key):
    seen_values = set()
    for obj in iterable:
        if key in obj:
            assert obj[key] not in seen_values
            seen_values.add(obj[key])

    return True


def parse(yaml_policy, vars=None, ignore_condition_ids=False):
    policy_template = jinja2.Template(yaml_policy)
    yaml_policy = policy_template.render(**vars or {})
    document = yaml.load(yaml_policy)
    policy = {}
    conditions = {}

    for key, value in document.items():
        if key in ['name', 'incident_preference']:
            policy[key] = value
        else:
            conditions[key] = value

    if not ignore_condition_ids:
        for condition_type_name, condition_list in conditions.items():
            try:
                assert_field_unique(condition_list, 'id')
            except AssertionError:
                sys.exit(
                    "Duplicate condition ID found in %s" % condition_type_name)

    return policy, conditions


def build_document(policy, conditions):
    document = {'name': policy['name'],
                'incident_preference': policy['incident_preference']}

    document.update(conditions)
    return document
