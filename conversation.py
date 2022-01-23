'Conversation module for Anxiety Free.'
import csv
import io
import logging

import requests

LOGGER = logging.getLogger('anx.conversation')


class InvalidFlow(Exception):
    'An invalid flow encountered.'


class Session:
    'Hold the context of a session.'
    instances = set()
    lines = {}

    def __init__(self):
        self.current_line = None
        self.placeholders = {}
        Session.instances.add(self)

    def resolve_placeholders(self):
        'Return the resolved bot text of the current line.'
        try:
            return self.current_line['bot_text'].format(**self.placeholders)
        except KeyError as key_error:
            return f"undefined placeholder '{key_error.args[0]}' on line '{self.current_line['name']}'"

    def next(self, answer):
        'Get the next bot text.'
        if self.current_line is None:
            try:
                self.current_line = Session.lines['start']
            except KeyError:
                return 'No start line found - try to update the bot lines and flows'
        else:
            self.placeholders[self.current_line['defines']] = answer
            if self.current_line == Session.lines['end']:
                self.current_line = None
                return 'You have reached the end of the session - restarting!'
            try:
                self.current_line = Session.lines[self.current_line['flow'][answer]]
            except KeyError:
                try:
                    self.current_line = Session.lines[self.current_line['flow'][None]]
                except KeyError:
                    answers = ', '.join(self.current_line['flow'].keys())
                    if answers:
                        return f"valid answers are: {answers}"
                    LOGGER.warning('reached a line with no flow, moving to end')
                    self.current_line = Session.lines['end']
        return self.resolve_placeholders()

    @classmethod
    def reset_sessions(cls):
        'Reset all sessions.'
        for instance in cls.instances:
            instance.current_line = None


def get_lines_from_editor():
    'Currently hard-coded - soon to be from a google sheet.'
    lines, flows = [list(reader) for reader in [csv.reader(io.StringIO(requests.get(
        'https://docs.google.com/spreadsheets/d/'
        '1gMXB15oikh5oo7xnlwpo9PdB7HL1TzXSyoR9096teVs'
        f"/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    ).text)) for sheet_name in ['lines', 'flows']]]
    lines = [dict(name=line[0], bot_text=line[1], defines=line[2] or None) for line in lines[1:]]
    flows = [dict(source=flow[0], answer=flow[1] or None, target=flow[2]) for flow in flows[1:]]
    return lines, flows


def combine_lines_and_flows(lines, flows):
    'Combine bot lines and flows into a convenient dict while validating the data.'
    lines = {line['name']: dict(line, flow={}) for line in lines}
    for flow in flows:
        for item_type in ['target', 'source']:
            if flow[item_type] not in lines:
                raise InvalidFlow(f"did not find required {item_type} line: {flow[item_type]}")
        lines[flow['source']]['flow'][flow['answer']] = flow['target']
    children = set()
    for line in lines.values():
        if 'flow' not in line or not line['flow']:
            line['flow'] = {}
        elif isinstance(line['flow'], str):
            line['flow'] = {None: line['flow']}
        for target in line['flow'].values():
            children.add(target)

    # Validate the data.
    all_lines = set(lines.keys())
    missing_lines = {'start', 'end'} - all_lines
    if missing_lines:
        raise InvalidFlow(f"did not find required line(s): {missing_lines}")
    orphan_lines = all_lines - children - {'start'}
    if orphan_lines:
        raise InvalidFlow(f"orphan lines found: {orphan_lines}")
    for flow in flows:
        if flow['source'] not in lines:
            raise InvalidFlow(f"invalid source {flow['source']} to {flow['target']} on {flow['answer']}")
        if flow['target'] not in lines:
            raise InvalidFlow(f"invalid target {flow['target']} from {flow['source']} on {flow['answer']}")

    return lines


def update_lines():
    'Delete the old data and insert the new.'
    lines_list, flows_list = get_lines_from_editor()
    Session.lines = combine_lines_and_flows(lines_list, flows_list)
    Session.reset_sessions()
