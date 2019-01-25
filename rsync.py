#!/usr/bin/env python3
import argparse
import os


def get_src(src):
    if '/' in src:
        return os.path.basename(src)
    return src


def get_dst(dst, filename):
    if os.path.isdir(dst):
        if dst[-1] != '/':
            return dst + '/' + filename
        else:
            return dst + filename
    return dst


def make_dir(dst):
    if not os.path.exists(dst) and '/' in dst:
        if dst[-1] == '/':
            os.mkdir(dst, 0o755)
        else:
            if not os.path.exists(os.path.dirname(dst)):
                os.mkdir(os.path.dirname(dst), 0o755)


def check_time(src, dst):
    if not os.path.exists(dst):
        return False
    return os.stat(src).st_mtime == os.stat(dst).st_mtime


def check_size(src, dst):
    if not os.path.exists(dst):
        return False
    return os.stat(src).st_size == os.stat(dst).st_size


def check_hard_link(file):
    return os.stat(file).st_nlink > 1


def check_sym_link(file):
    return os.path.islink(file)


def update_content(src, dst):
    try:
        f2 = os.open(dst, os.O_RDWR | os.O_CREAT)
    except PermissionError:
        os.unlink(dst)
        os.link(src, dst)
        return
    f1 = os.open(src, os.O_RDONLY)
    srcstr = os.read(f1, os.path.getsize(src))
    f2 = os.open(dst, os.O_RDWR | os.O_CREAT)
    dststr = os.read(f2, os.path.getsize(dst))
    count = 0
    while count < os.path.getsize(src):
        os.lseek(f1, count, 0)
        os.lseek(f2, count, 0)
        if count < len(dststr):
            if dststr[count] != srcstr[count]:
                os.write(f2, os.read(f1, 1))
        else:
            os.write(f2, os.read(f1, 1))
        count = count + 1


def copy_link(src, dst):
    if os.path.exists(dst):
        os.unlink(dst)
    if check_sym_link(src):
        linkto = os.readlink(src)
        os.symlink(linkto, dst)
    elif check_hard_link(src):
        os.link(src, dst)


def update_time_and_per(src, dst):
    if not check_sym_link(src):
        statsrc = os.stat(src)
        os.chmod(dst, statsrc.st_mode)
        os.utime(dst, (statsrc.st_atime, statsrc.st_mtime))
    else:
        statsrc = os.lstat(src)
        os.utime(dst,
                 (statsrc.st_atime, statsrc.st_mtime), follow_symlinks=False)


def copy_file(src, dst):
    f1 = os.open(src, os.O_RDONLY)
    if check_hard_link(src) or check_sym_link(src):
        copy_link(src, dst)
    else:
        if os.path.exists(dst) and os.stat(src).st_size >= \
         os.stat(dst).st_size:
            update_content(src, dst)
        else:
            if os.path.exists(dst):
                os.unlink(dst)
            f2 = os.open(dst, os.O_WRONLY | os.O_CREAT)
            os.write(f2, os.read(f1, os.path.getsize(src)))


def check_value(src, dst, update, checksum):
    if checksum:
        return True
    if update:
        if os.stat(src).st_mtime > os.stat(dst).st_mtime:
            return True
        else:
            return False
    if not check_time(src, dst) or not check_size(src, dst):
        return True
    return False


def rec_dir(src, dst, update, checksum, rec):
    make_dir(dst)
    folders = []
    files = []
    for entry in os.scandir(src):
        if entry.is_dir():
            folders.append(entry.path)
        elif entry.is_file():
            files.append(entry.path)
    for i in files:
        temp = get_dst(dst,  get_src(i))
        rsync(i, temp, update, checksum, False)
    for i in folders:
        rsync(i, dst, update, checksum, rec)


def rsync(src, dst, update, checksum, rec):
    if not os.path.exists(src):
        print("rsync: link_stat \"" + os.path.abspath(src) + "\" failed:\
 No such file or directory (2)")
        return
    try:
        f1 = os.open(src, os.O_RDONLY)
    except PermissionError:
        if os.path.isfile(src):
            print("rsync: send_files failed \
to open \""+os.path.abspath(src)+"\": Permission denied (13)")
        return
    if rec:
        make_dir(dst + '/')
        if src[-1] != '/':
            dst = get_dst(dst,  get_src(src)) + '/'
        rec_dir(src, dst, update, checksum, rec)
    elif os.path.isfile(src):
        make_dir(dst)
        dst = get_dst(dst,  get_src(src))
        if check_value(src, dst, update, checksum):
            copy_file(src, dst)
            update_time_and_per(src, dst)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('SRC_FILE', nargs='+', type=str)
    parser.add_argument('DESTINATION', type=str)
    parser.add_argument("-u", "--update", action='store_true', help='skip\
                files that are newer on the receiver')
    parser.add_argument("-c", "--checksum", action='store_true', help='skip\
                based on checksum, not mod-time & size')
    parser.add_argument("-r", "--recursive", action='store_true', help='\
                recurse into directories')
    arg = parser.parse_args()
    for i in arg.SRC_FILE:
        rsync(i, arg.DESTINATION, arg.update, arg.checksum, arg.recursive)


if __name__ == "__main__":
    main()
