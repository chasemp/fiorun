#!/usr/bin/python
import uuid
import argparse
import itertools
import logging
import os
import shutil
import sys
import subprocess
import time

"""
Job types to run:

1.  seq write 2x RAM+ (write) (direct 0,1)
2.  seq read  2x RAM+ (read) (direct 0,1)
3.  seq read/write mix (readwrite) (1024k, 5M, 100M, 1G) (numjobs 10, 50, 100, 150, 200) (time 60, 240, 360)
4.  random read size (randread) (1024k, 5M, 100M, 1G) (numjobs 10, 50, 100, 150, 200) (time 60, 240, 360)
5.  random write size (randwrite) (1024k, 5M, 100M, 1G) (numjobs 10, 50, 100, 150, 200) (time 60, 240, 360)
6.  rand read/write mix (randrw) (1024k, 5M, 100M, 1G) (numjobs 10, 50, 100, 150, 200)  (time 60, 240, 360)
"""

sequential = {
            'readwrite': ['read', 'write', 'readwrite'],
            'direct': [0, 1],
            'ioengine': ['sync'],
            'size': ['250G', '100G'],
            'numjobs': [1],
            'runtime': [360, 720],
            'runtime': [60],
            'bs': ['1024k', '1M'],
}

random = {
            'readwrite': ['randread', 'randwrite', 'randrw'],
            'direct': [0, 1],
            'ioengine': ['libaio'],
            'size': ['1024k', '5M', '100M', '1G'],
            'numjobs': [5, 50, 150, 200],
            'runtime': [60, 350],
}

jobs = {
    '/mnt/RAID10': [sequential, random],
    '/mnt/LVMRAID1STRIPES/': [sequential, random],
}


class Timer:
    def __enter__(self):
        self.start = time.clock()
        return self

    def __exit__(self, *args):
        self.end = time.clock()
        self.interval = self.end - self.start


def rec_remove(path):
    for root, dirs, files in os.walk(path):
        for f in files:
    	    os.unlink(os.path.join(root, f))
        for d in dirs:
    	    shutil.rmtree(os.path.join(root, d))


def expand_jobs(**kwargs):
    """find all possible combinations of options in test arrays"""
    options = []
    for k, values in kwargs.iteritems():
       name_values = []
       for v in values:
           name_values.append("--%s=%s" % (k, v))
       options.append(name_values)
    return list(itertools.product(*options))


def job_name(job):
    """ find a friendly name for the job defined"""
    return '_'.join(j for j in job).replace('=', '-').replace('--','')


def fio(name, job):
    """ append name, fio binary path, and run the job"""
    job.append('--name=%s' % name,)
    job.insert(0,'/usr/bin/fio')
    return subprocess.check_output(job)

def die(msg):
    print msg
    sys.exit(1)

def safety_check():

    try:
        subprocess.check_output(['fio', '-h'])
    except OSError:
        die('fio binary cannot be found.')

def testid():
    return uuid.uuid4().hex[-8:]


def main():

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('out_dir', metavar='O', type=str, nargs='+',
                    help='directory to drop output files into', default='/tmp')
    parser.add_argument('-d', action='store_true')
    args = parser.parse_args()

    out_dir = args.out_dir[0]

    loglvl=logging.INFO
    if args.d:
        loglvl=logging.DEBUG

    logging.basicConfig(level=loglvl)
    logging.info("Output directory: %s" % (out_dir,))

    safety_check()

    all_jobs = {}
    for path, jdefine in jobs.iteritems():
        logging.info("%s processing jobs" % (path,))
        all_jobs[path] = []
        for defined in jdefine:
            all_jobs[path] += expand_jobs(**defined)

        logging.info("%s -- %s distinct jobs" % (path, len(all_jobs[path])))

    # collapse all jobs for a count
    j = list(itertools.chain.from_iterable([v for k, v in all_jobs.iteritems()]))
    total_jobs = len(j)
    logging.info("\n\nRunning %s jobs across %s mounts\n" % (total_jobs, len(all_jobs.keys())))

    run_jobs = 0
    for path, distinct_jobs in all_jobs.iteritems():
        os.chdir(path)
        for job in distinct_jobs:
            logging.info("Remaining: %s/%s" % (total_jobs - run_jobs, total_jobs))
            logging.info("%s job: %s" % (path, ' '.join(job)))
            metadata = {}
            job = list(job)
            name = job_name(job)

            with Timer() as t:
                out = fio(name, job)
                rec_remove(path)

            sec = round(t.interval * 1000, 2)
            metadata['sec'] = sec
            with open('/proc/loadavg', 'r') as loadavg:
                load = loadavg.read()

            metadata['load'] = load
            sanitized_path = path.replace('/', '_').lstrip('_')
            outfile = '%s/%s-%s.txt' % (out_dir, sanitized_path, name)

            out += '\n-----------------\n'
            for meta, data in metadata.iteritems():
                metavalue = "%s = %s" % (meta, data)
                out += metavalue
                logging.debug(metavalue)
            out += '\n'

            with open(outfile, 'w') as f:
                f.write(out)

            logging.info("\nCreated --> %s" % (outfile,))
            run_jobs += 1


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
