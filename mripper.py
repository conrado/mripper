
import os
import sys
import re
import pexpect as p
import datetime

import logging
logging.basicConfig(level=logging.DEBUG)

####### defaults
command = 'streamripper'

stream_uri = 'http://pub2.sky.fm:80/sky_rootsreggae'

user_agent_flag = '-u'
user_agent = '"MRipper 0.0.1 (http://github.com/conrado/mripper)"'

rip_to = os.path.join(os.path.expanduser("~"), '.mripper', 'ripped')

filematch_re = r'\[.*\](.*)\[' # is this where they inject us?

extra_flags = '-r 8080'
#######

def check_self_dir():
    global rip_to
    if not os.path.exists(rip_to):
        os.makedirs(rip_to)

def build_rip_command(command=command, stream_uri=stream_uri,
        user_agent_flag=user_agent_flag, user_agent=user_agent):
    return '%s %s %s %s %s' % (command, stream_uri, extra_flags,
            user_agent_flag, user_agent)

def write_to_file(output):
    with open('out', 'a') as f:
        f.write(output)

def log_playlist_to_file(playlist, filename):
    with open('%s/playlist.log'%rip_to, 'a') as f:
        s = "<played><playlist>%s</playlist><track>%s</track><date>%s</date></played>\n" % (playlist, filename, datetime.datetime.now())
        f.write(s)


SKIPPING = 0
RIPPING = 1
BUFFERING = 2
UNKNOWN = -1
states = {
        SKIPPING: '[skipping...',
        RIPPING: '[ripping...',
        BUFFERING: '[buffering'
}
def state(line):
    for state, startstring in states.items():
        if line.startswith(startstring):
            return state
    return UNKNOWN


filere=re.compile(filematch_re)
def extract_filename(line):
    filename_start = None
    match=filere.match(line)
    if match:
        filename_start = match.group(1).strip()
    return filename_start


NOTHING = 0
PROCESS_FILE = 1
DELETE_INCOMPLETE = 2
UNDETERMINED_ACTION = -1
def determine_action(previous_state, current_state, previous_file, current_file):
    if previous_file == current_file:
        return NOTHING
    if current_state == RIPPING:
        return PROCESS_FILE
    if current_state == SKIPPING:
        return DELETE_INCOMPLETE
    return UNDETERMINED_ACTION

def handle_PROCESS_FILE(filename):
    logging.debug('Processing File: %s' %filename)
    log_playlist_to_file(stream_uri,filename)

def handle_DELETE_INCOMPLETE(filename):
    logging.debug('Deleting incomplete file: %s' %filename)

def handle_NOTHING(filename):
    logging.debug('Doing nothing: %s' %filename)

def handle_UNDETERMINED_ACTION(filename):
    logging.debug('Something went wrong with: %s' %filename)

perform = {
    PROCESS_FILE : handle_PROCESS_FILE,
    DELETE_INCOMPLETE: handle_DELETE_INCOMPLETE,
    NOTHING : handle_NOTHING,
    UNDETERMINED_ACTION : handle_UNDETERMINED_ACTION
}

previous_state = UNKNOWN
previous_file = None
def handle(line):
    global previous_file
    global previous_state
    current_state = state(line)
    current_file = extract_filename(line)
    if current_file:
        action = determine_action(previous_state, current_state,
                                  previous_file, current_file)
        perform[action](current_file)
        previous_file = current_file
        previous_state = current_state

def extract_last_line(line):
    return line.strip().split('\r')[-1:][0]

def main():

    global rip_to
    kwargs={
      'logfile': open(os.path.join(os.path.expanduser("~"), 'mripper.log'),'w'),
      'cwd': rip_to,
      'timeout': None
    }
    check_self_dir()
    command = build_rip_command()
    logging.debug('Running command: %s' %command)
    c = p.spawn(command, **kwargs)

    running = True
    b = ''
    while(running):
        char = c.read_nonblocking(timeout=None)
        b += char
        sys.stdout.write('%s' % char)
        sys.stdout.flush()
        #write_to_file(char)
        if char=='\n':
            line = extract_last_line(b)
            handle(line)
            b = ''

if __name__ == '__main__':
    main()
