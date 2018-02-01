"""Script for parsing the logs from the SampleApp
"""
import argparse
import re
from datetime import datetime
import csv
import json


# Regexes used to parse out log statements
re_lib_log = re.compile("(\d\d\d\d)-(\d\d)-(\d\d)\s(\d\d):(\d\d):(\d\d).(\d\d\d)\s\[.+\]\s([A-Za-z0-9])\s([A-Za-z0-9]+):([A-Za-z0-9]+):(.+=.+)*")
re_keys = re.compile("([A-Za-z0-9]+)=")
re_values = re.compile("=([A-Za-z0-9]+|\{.+\})")


class LibraryLog:
    """Log statement 
    """
    def __init__(self, year, month, day, hour, mins, secs, mils, lvl, cls, mthd, vals):
        """Constructor
        """
        self.ts = datetime(int(year), int(month), int(day), int(hour), 
                int(mins), int(secs), int(mils))
        self.level = lvl
        self.cls = cls 
        self.method = mthd
        self.values = {}

        if len(vals) > 0:
            keys = re_keys.findall(vals)
            values = re_values.findall(vals)
            for k, v in zip(keys, values):
                try:
                    cleaned = v.replace('\\:', '":').replace('\\,', ',"')
                    self.values[k] = json.loads(cleaned)
                except ValueError:
                    self.values[k] = v

    def __str__(self):
        return '{} - {}: {}:{} - {}'.format(
                self.ts, self.level, self.cls, self.method, self.values) 
        

class Results:
    """Results of analyzing the log file
    """
    def __init__(self):
        self.dialog_state_trans = []
        self.audio_input_state_trans = []
        self.stop_capture_times = []
        self.errors = []
        self.directives = []
        self.keyword_recognitions = 0
        self.is_listening = False
    
    def add_dialog_state_change(self, ts, from_state, to_state):
        data = {'start_ts': ts, 'end_ts': None, 'from': from_state, 'to': to_state}

        if self.dialog_state_trans:
            self.dialog_state_trans[-1]['end_ts'] = ts

        self.dialog_state_trans.append(data)

        if to_state == 'LISTENING':
            self.is_listening = True
            self.stop_capture_times.append({'start_ts': ts, 'end_ts': None})

    def add_stop_capture(self, ts):
        self.is_listening = False
        if self.stop_capture_times[-1]['end_ts'] is not None:
            raise RuntimeError('Stop capture without listening state change..')
        self.stop_capture_times[-1]['end_ts'] = ts

    def add_audio_input_state_change(self, ts, from_state, to_state):
        data = {'start_ts': ts, 'end_ts': None, 'from': from_state, 'to': to_state}
        if self.audio_input_state_trans:
            self.audio_input_state_trans[-1]['end_ts'] = ts

        self.audio_input_state_trans.append(data)

        if to_state == 'RECOGNIZING':
            self.keyword_recognitions += 1

    def add_error(self, log):
        self.errors.append(log)

    def add_directive(self, log):
        self.directives.append(log)

    def write_errors(self, filename):
        with open(filename, 'w') as f:
            for err in self.errors:
                f.write('{}\n'.format(str(err)))

    def write_directives(self, filename):
        with open(filename, 'w') as f:
            for directive in self.directives:
                f.write('{}\n'.format(str(directive)))

    def write_to_csv(self, filename):
        data = []
        # CSV header
        header = ['start', 'end', 'elapsed (sec)', 'Stop Capture',
                'Dialog From State', 'Dialog To State', 
                'AIP From State', 'AIP To State',
                'Total Keyword Detections', 'Number of Errors']

        # joining all data together
        for ds_trans in self.dialog_state_trans:
            data.append(self._create_data_entry(
                ds_trans['start_ts'], ds_trans['end_ts'], 
                ds_from=ds_trans['from'], ds_to=ds_trans['to']))

        for aip_trans in self.audio_input_state_trans:
            data.append(self._create_data_entry(
                aip_trans['start_ts'], aip_trans['end_ts'],
                aip_from=aip_trans['from'], aip_to=aip_trans['to']))

        for sc in self.stop_capture_times:
            data.append(self._create_data_entry(
                sc['start_ts'], sc['end_ts'], sc=True))

        # Sorting the data by the start time stamp
        data = sorted(data, key=lambda i: i['start'])

        data[0]['Total Keyword Detections'] = self.keyword_recognitions
        data[0]['Number of Errors'] = len(self.errors)

        with open(filename, 'w') as f:
            writer = csv.DictWriter(f, header)
            writer.writeheader()
            for i in data:
                if i['start'] is not None:
                    i['start'] = i['start'].strftime('%b %a %d %Y - %H:%M:%S.%f')
                if i['end'] is not None:
                    i['end'] = i['end'].strftime('%b %a %d %Y - %H:%M:%S.f')
                writer.writerow(i)

    def _create_data_entry(self, start, end, sc=False, ds_from=None, 
            ds_to=None, aip_from=None, aip_to=None, num_detections=None,
            num_errors=None):
        if end is None or start is None:
            elapsed = None
        else:
            elapsed = (end - start).total_seconds()
        return {
            'start': start,
            'end': end,
            'elapsed (sec)': elapsed,
            'Stop Capture': sc,
            'Dialog From State': ds_from,
            'Dialog To State': ds_to,
            'AIP From State': aip_from,
            'AIP To State': aip_to,
            'Total Keyword Detections': num_detections,
            'Number of Errors': num_errors
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='Input log file')
    parser.add_argument('csv_output', help='CSV results output for the log file')
    parser.add_argument('errors_output', help='Error logs output')
    parser.add_argument('directives_output', help='Received directives output')
    args = parser.parse_args()
    results = Results()
    data = None

    print('-- Reading log file :', args.input)
    with open(args.input, 'r') as f:
        data = f.read()

    print('-- Parsing and analyzing logs')
    for i in re_lib_log.findall(data):
        lib = LibraryLog(*i)
        if lib.cls == 'DialogUXStateAggregator' and lib.method == 'setState':
            results.add_dialog_state_change(
                    lib.ts, lib.values['from'], lib.values['to'])
        elif lib.cls == 'AudioInputProcessor' and lib.method == 'setState':
            results.add_audio_input_state_change(
                    lib.ts, lib.values['from'], lib.values['to'])
        elif lib.cls == 'DirectiveSequencer' and lib.method == 'onDirective':
            directive = lib.values['directive']
            results.add_directive(lib)
            if directive['name'] == 'StopCapture':
                results.add_stop_capture(lib.ts)
        elif lib.level == 'E' and (lib.cls != 'AbstractKeywordDetector' 
                and lib.method != 'readFromStreamFailed'):
            results.add_error(lib)

    print('-- Writing :', args.csv_output)
    results.write_to_csv(args.csv_output)
    print('-- Writing :', args.errors_output)
    results.write_errors(args.errors_output)
    print('-- Writing :', args.directives_output)
    results.write_directives(args.directives_output)

    print('-- Done.')

if __name__ == '__main__':
    main()

