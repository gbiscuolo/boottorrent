# -*- coding: utf-8 -*-

"""Main module."""
from distutils.dir_util import copy_tree
from jinja2 import Template
import json
import os
import pathlib
import queue
import requests
import shutil
import signal
import subprocess
import threading
import time
import yaml


class BootTorrent:
    def __init__(self, config, wd):
        self.assets = os.path.dirname(__file__) + "/assets"
        self.config = config
        self.output = queue.Queue()
        self.process = dict({})
        self.threads = dict({})
        self.wd = wd

    def sigint_handler(self, signal, frame):
        print('Attempting to terminate the processes...')
        for _, process in self.process.items():
            process.terminate()
        # Putting None ends the output thread
        self.output.put(None)

    def start(self):
        signal.signal(signal.SIGINT, self.sigint_handler)
        self.recreate_output_dir()
        self.configure_dnsmasq()
        self.generate_torrents()
        self.generate_initrd()
        self.configure_transmission_host()

        t_thread = threading.Thread(
                target=self.start_process_transmission,
                )
        self.threads['transmission'] = t_thread
        d_thread = threading.Thread(
                target=self.start_process_dnsmasq,
                )
        self.threads['dnsmasq'] = d_thread
        o_thread = threading.Thread(
                target=self.display_output,
                )
        self.threads['output'] = o_thread

        for _, val in self.threads.items():
            val.start()

        # wait for the transmission process to start and
        # initialize before adding torrents
        time.sleep(3)
        self.add_generated_torrents()

        # wait for threads to finish before exiting
        for _, val in self.threads.items():
            val.join()

    def display_output(self):
        while True:
            # Set as blocking because the function is launched as a thread.
            line = self.output.get(block=True, timeout=None)
            if line is None:
                break
            print(line, end="")
            self.output.task_done()

    def add_generated_torrents(self):
        port = self.config['transmission']['seed']['rpc_port']
        # get X-Transmission-Session-Id; To make torrent-add request later
        text = requests.get(f"http://localhost:{port}/transmission/rpc").text
        csrftoken = text[522:570]
        with open(self.wd + '/out/torrents/list.yaml', 'r') as f:
            data = f.read()
            oss = yaml.load(data)
        for os in oss:
            args = {
                    'paused': False,
                    'download-dir': f"{self.wd}/oss",
                    'filename': f"{self.wd}/out/torrents/{os}.torrent",
                    }
            req = requests.post(
                    f"http://localhost:{port}/transmission/rpc",
                    data = json.dumps({
                        "method": "torrent-add",
                        "arguments": args,
                        }),
                    headers = {
                        'X-Transmission-Session-Id': csrftoken,
                        }
                    )
            if req.status_code == 200:
                self.output.put(f"TRANSMISSION: Added torrent for {os}.\n")

    def configure_dnsmasq(self):
        self.config['dnsmasq']['dhcp_leasefile'] = (
                self.wd
                + '/out/dnsmasq/dnsmasq.leases'
                )
        self.config['dnsmasq']['ph1'] = self.wd+'/out/dnsmasq/ph1'
        self.config['dnsmasq']['enable_tftp'] = True
        with open(self.assets+'/tpls/dnsmasq.conf.tpl', 'r') as dnsmasqtpl:
            data = dnsmasqtpl.read()
            dnsmasqconf = Template(data).render(**self.config['dnsmasq'])
        with open(self.wd+'/out/dnsmasq/dnsmasq.conf', 'w') as dnsmasqfile:
            dnsmasqfile.write(dnsmasqconf)

    def configure_transmission_host(self):
        self.config['transmission']['seed']['osdir'] = self.wd+'/oss'
        with open(self.assets+'/tpls/transmission.json.tpl', 'r') as f:
            data = f.read()
            transmissionconf = Template(data).render(
                    **self.config['transmission']['seed']
                    )
        with open(self.wd+'/out/transmission/settings.json', 'w') as f:
            f.write(transmissionconf)

    def start_process_dnsmasq(self):
        process = subprocess.Popen(
                ['dnsmasq', '-C', f'{self.wd}/out/dnsmasq/dnsmasq.conf'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                )
        self.process['dnsmasq'] = process
        for line in process.stdout:
            self.output.put(f"DNSMASQ: {line}")

    def start_process_transmission(self):
        process = subprocess.Popen(
                [
                    'transmission-daemon',
                    '-f', '-g',
                    f'{self.wd}/out/transmission',
                    ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                )
        self.process['transmission'] = process
        for line in process.stdout:
            self.output.put(f"TRANSMISSION: {line}")

    def generate_torrents(self):
        oss = self.config['boottorrent']['display_oss']
        oslist = []
        for os in oss:
            filename = f"{self.wd}/out/torrents/{os}.torrent"
            p = subprocess.Popen(
                    [
                        'transmission-create',
                        self.wd + '/oss/' + os,
                        '-o', filename,
                        ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                )
            p.wait()
            oslist.append(os)
            shutil.copyfile(
                    f"{self.wd}/oss/{os}/config.yaml",
                    f"{self.wd}/out/torrents/{os}.yaml",
                    )
            for line in p.stdout:
                self.output.put(f"TRANSMISSION-CREATE: {line}\n")
        with open(self.wd + '/out/torrents/list.yaml', 'w') as f:
            f.write(yaml.dump(oslist))

    def generate_initrd(self):
        t = subprocess.Popen([
            'bsdtar',
            '-c', '--format', 'newc', '--lzma',
            '-f', self.wd+'/out/dnsmasq/ph1/torrents.gz',
            '-C', self.wd+'/out',
            'torrents',
            ])
        t.wait()

    def recreate_output_dir(self):
        shutil.rmtree(self.wd + "/out", ignore_errors=True)
        pathlib.Path.mkdir(
                pathlib.Path(self.wd + "/out/dnsmasq"),
                parents=True,
                exist_ok=False,
                )
        copy_tree(self.assets+"/ph1", self.wd + "/out/dnsmasq/ph1")
        pathlib.Path.mkdir(
                pathlib.Path(self.wd + "/out/torrents"),
                parents=True,
                exist_ok=False,
                )
        pathlib.Path.mkdir(
                pathlib.Path(self.wd + "/out/transmission"),
                parents=True,
                exist_ok=False,
                )
