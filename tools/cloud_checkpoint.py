"""GitHub contents API checkpoint store; only called by the manual cloud workflow.

Durable branch history, optimistic SHA checks, no cache dependency. HTTP errors
fail closed: a missing/corrupt existing checkpoint never resets the story.
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autonomy.checkpoint import capture, envelope, unpack, restore, refuse_regression
from autonomy.contracts import write_json

BRANCH = 'autonomy-state'
FILE = 'checkpoint/story.json'


class GitHub:
    def __init__(self):
        self.repository = os.environ['GITHUB_REPOSITORY']
        self.token = os.environ['GH_TOKEN']

    def call(self, method, route, data=None):
        request = urllib.request.Request('https://api.github.com/repos/' + self.repository + '/' + route,
            data=None if data is None else json.dumps(data).encode(), method=method,
            headers={'Authorization': 'Bearer ' + self.token, 'Accept': 'application/vnd.github+json',
                     'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'shorts-story-checkpoint'})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 404 and method == 'GET':
                return None
            raise RuntimeError('GitHub checkpoint API failed: HTTP ' + str(error.code)) from None


def recover(api, seed, state, receipt):
    branch = api.call('GET', 'git/ref/heads/' + BRANCH)
    remote = api.call('GET', 'contents/' + FILE + '?ref=' + BRANCH) if branch else None
    if branch and not remote:
        raise RuntimeError('Existing state branch has no checkpoint; restore its history, never reset it')
    seed_value = json.loads(Path(seed).read_text())
    value = json.loads(base64.b64decode(remote['content'])) if remote else seed_value
    snapshot = unpack(value)
    refuse_regression(unpack(seed_value), snapshot)
    restore(snapshot, state)
    write_json(receipt, {'sha': remote['sha'] if remote else None, 'previous': snapshot,
                         'branch_exists': bool(branch)})
    print('CHECKPOINT RESTORED: source=' + ('durable branch' if remote else 'reviewed Episode 2 seed') +
          '; verified=' + str(sum(e['status']=='verified' for e in snapshot['episodes'])), flush=True)


def persist(api, state, receipt):
    prior = json.loads(Path(receipt).read_text())
    current = capture(state)
    refuse_regression(prior['previous'], current)
    if not prior['branch_exists']:
        # Create one branch and checkpoint commit atomically. No empty branch window.
        base = os.environ['GITHUB_SHA']
        commit = api.call('GET', 'git/commits/' + base)
        tree = api.call('POST', 'git/trees', {'base_tree': commit['tree']['sha'], 'tree': [
            {'path': FILE, 'mode': '100644', 'type': 'blob', 'content': json.dumps(envelope(current), indent=2)}]})
        created = api.call('POST', 'git/commits', {'message': 'Initialize durable story checkpoint through Episode 2',
            'tree': tree['sha'], 'parents': [base]})
        api.call('POST', 'git/refs', {'ref': 'refs/heads/' + BRANCH, 'sha': created['sha']})
        remote = api.call('GET', 'contents/' + FILE + '?ref=' + BRANCH)
        prior['sha'], prior['branch_exists'] = remote['sha'], True
    else:
        result = api.call('PUT', 'contents/' + FILE, {
            'message': 'Checkpoint autonomous run ' + os.environ.get('GITHUB_RUN_ID', 'manual'),
            'content': base64.b64encode(json.dumps(envelope(current),indent=2).encode()).decode(),
            'sha': prior['sha'], 'branch': BRANCH})
        prior['sha'] = result['content']['sha']
    prior['previous'] = current
    write_json(receipt, prior)
    print('CHECKPOINT SAVED: branch=' + BRANCH + '; episodes=' + str(len(current['episodes'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['restore', 'save'])
    parser.add_argument('--state', default='state/story.sqlite3')
    parser.add_argument('--receipt', default='state/cloud_checkpoint.json')
    args = parser.parse_args()
    api = GitHub()
    if args.command == 'restore':
        recover(api, ROOT/'config/story_checkpoint.json', ROOT/args.state, ROOT/args.receipt)
    else:
        persist(api, ROOT/args.state, ROOT/args.receipt)
