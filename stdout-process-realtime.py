# Code for execute and get in real time each stdout generated character by the subprocess.
import subprocess

llama_exec = 'main.exe '
args = ['--model', 'model/open-llama-3b-q4_0.bin', '-c', '512', '--temp', '0.1', '--prompt', 'Hello how are', '-n', '100', '--verbose-prompt']

def capture_stdout_realtime(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=1, shell=True, universal_newlines=True)
    while True:
        char = process.stdout.read(1)
        if char == '' and p.poll() is not None:
            break
        if char != '':
            print(char, end='', flush=True)

capture_stdout_realtime([llama_exec] + args)
