"""Validate the four recorded executions. Does not invoke a model."""
import hashlib
import json
from pathlib import Path


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f'Invalid JSON constant: {value}')


def same(actual, expected):
    if expected is None:
        return actual is None
    if isinstance(expected, dict):
        return type(actual) is dict and actual.keys() == expected.keys() and all(same(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return type(actual) is list and len(actual) == len(expected) and all(same(a, b) for a, b in zip(actual, expected))
    if type(expected) in (int, float):
        return type(actual) in (int, float) and actual == expected
    return type(actual) is type(expected) and actual == expected


def main():
    root = Path(__file__).resolve().parent
    expected = json.loads((root / 'expected.json').read_text(encoding='utf-8'))
    results = json.loads((root / 'results.json').read_text(encoding='utf-8'))
    hashes = {item['case_id']: item['answer_sha256'] for item in results['executions']}
    for case, item in expected.items():
        raw = (root / 'execution' / case / 'answer.txt').read_bytes()
        actual = json.loads(raw.decode('utf-8'), parse_constant=reject_constant, object_pairs_hook=unique_object)
        if not same(actual, item['expected']):
            raise ValueError(f'Unexpected structure, types or values: {case}')
        if case.startswith('template') and any(list(row) != ['seller', 'amount', 'currency'] for row in actual):
            raise ValueError(f'Unexpected key order: {case}')
        if hashlib.sha256(raw).hexdigest() != hashes[case]:
            raise ValueError(f'Recorded answer changed: {case}')
        print(f'PASS {case}')
    for item in results['actors']:
        evidence = item['evidence']
        if evidence['quote'] not in (root / evidence['file']).read_text(encoding='utf-8'):
            raise ValueError(f'Evidence quote missing: {item["case_id"]}')
    print(f'Checked {len(expected)} recorded executions and {len(results["actors"])} evidence quotations.')


if __name__ == '__main__':
    main()
