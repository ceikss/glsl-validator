#!/usr/bin/python
import argparse
import os
import platform
import re
import shutil
import subprocess

DIR=os.path.dirname(os.path.realpath(__file__))

# Select the correct essl_to_glsl executable for this platform
if platform.system() == 'Darwin':
    ESSL_TO_GLSL = os.path.join(DIR, "angle/essl_to_glsl_osx")
elif platform.system() == 'Linux':
    ESSL_TO_GLSL = os.path.join(DIR, "angle/essl_to_glsl_linux")
elif platform.system() == 'Windows':
    ESSL_TO_GLSL = os.path.join(DIR, "angle/essl_to_glsl_win.exe")
else:
    print "Unsupported platform"
    exit(1)

args = {}

# Color terminal output
def color(s, color):
    if args.color:
        return "\033[1;%dm%s\033[1;m" % (color, s)
    else:
        return s

def grey(s):
    return color(s, 30)

def load_shader(shader_file):
    output = ""
    # Keep track of line numbers, #including will result in some corresponding to other files
    line_labels = []
    with open(shader_file, 'r') as f:
        line_num = 1
        for line in f:
            include_match = re.match("#include (.*)", line)
            if include_match:
                include_file = include_match.group(1)
                fullpath = os.path.join(os.path.dirname(shader_file), include_file)
                (included_shader, included_line_labels) = load_shader(fullpath)
                output += included_shader
                line_labels += included_line_labels
            else:
                output += line
                line_labels.append("%s:%d" % (shader_file, line_num))
            line_num += 1
    return (output, line_labels)

def validate_shader(shader_file):
    extension = os.path.splitext(shader_file)[1]
    tmp_file_name = "tmp%s" % extension

    # Load in the prefix for the shader first and then append the actual shader
    prefix_shader_file = os.path.join(DIR, "prefix/prefix%s" % extension)
    (prefix_shader, prefix_line_labels) = load_shader(prefix_shader_file)
    (shader, line_labels) = load_shader(shader_file)
    shader = prefix_shader + shader
    line_labels = prefix_line_labels + line_labels
    with open(os.path.join(DIR, tmp_file_name), 'w') as f:
        f.write(shader)

    # Run essl_to_glsl over the shader, reporting any errors
    p = subprocess.Popen([ESSL_TO_GLSL,
                          "-s=w",
                          "-x=d",
                          os.path.join(DIR, tmp_file_name)],
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT)
    ret_code = p.wait()
    os.remove(os.path.join(DIR, tmp_file_name))

    if ret_code != 0:
        raw_errors = p.stdout.readlines()[1:-4]

        # Write out formatted errors
        error = ""
        for e in raw_errors:
            # Error format is: 'ERROR: 0:<line number>: <error message>
            details = re.match("ERROR: 0:(\d+): (.*)", e)
            line_number = int(details.group(1))
            line_label = line_labels[line_number-1]
            error_message = details.group(2)
            error_format = grey("%s ") + "%s\n"
            error += error_format % (line_label, error_message)
        print error
        exit(1)

def standalone():
    parser = argparse.ArgumentParser(description='Validate three.js shaders')
    parser.add_argument('files', metavar='FILE', type=str, nargs='+',
                               help='files to validate')
    parser.add_argument('--color', dest='color', action='store_true', help='Color output')
    parser.add_argument('--no-color', dest='color', action='store_false', help='Color output')
    parser.set_defaults(color=True)
    global args
    args = parser.parse_args()
    files = args.files
    bad_extensions = filter(lambda f: not re.match('^\.(vert|frag)$', os.path.splitext(f)[1]), files)
    for f in bad_extensions:
        print "Invalid file: %s, only support .frag and .vert files" % f
        exit(1)

    map(validate_shader, files)

if __name__ == "__main__":
    standalone()
