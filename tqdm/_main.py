from ._tqdm import tqdm
from ._version import __version__  # NOQA
import os
import sys
import re
__all__ = ["main"]
__author__ = "github.com/casperdcl"


"""
Note: as a general rule in case of errors, we pipe all stdin>out
before raising the exception.
"""


class TqdmTypeError(TypeError):
    pass


class TqdmKeyError(KeyError):
    pass


def cast(val, typ):
    # sys.stderr.write('\ndebug | `val:type`: `' + val + ':' + typ + '`.\n')
    if typ == 'bool':
        if (val == 'True') or (val == ''):
            return True
        elif val == 'False':
            return False
        else:
            raise TqdmTypeError(val + ' : ' + typ)
    try:
        return eval(typ + '("' + val + '")')
    except:
        if (typ == 'chr'):
            return chr(ord(eval('"' + val + '"')))
        else:
            raise TqdmTypeError(val + ' : ' + typ)


def posix_pipe(fin, fout, delim='\n', buf_size=256,
               callback=lambda int: None  # pragma: no cover
               ):
    """
    Should be noexcept.

    Params
    ------
    fin  : file with `fileno()` or `read(buf_size : int)` method.
    fout  : file with `write` (and optionally `flush`) methods.
    callback  : function(int), e.g.: `tqdm.update`
    """
    # buf_size = 1 if delim == '\n' else buf_size
    try:
        fpi = os.fdopen(os.dup(fin.fileno()), mode="r" + "bt"[bool(buf_size)],
                        buffering=buf_size, newline='')
    except:
        fp_read = fin.read
    else:
        fp_read = fpi.read

    try:
        obsize = 0
        if sys.version_info[0] == 3:
            os.environ['PYTHONUNBUFFERED'] = '1'
            obsize = 1
        # unbuffered is slightly slower but more POSIX filter compliant
        fpo = os.fdopen(os.dup(fout.fileno()), mode="a" + "bt"[obsize],
                        buffering=obsize, newline='')
    except:
        fp_write = fout.write
    else:
        fp_write = fpo.write

    buf = ''
    tmp = ''
    # n = 0
    while True:
        tmp = fp_read(buf_size)

        # flush at EOF
        if not tmp:
            if buf:
                fp_write(buf)
                callback(1 + buf.count(delim))  # n += 1 + buf.count(delim)
            return  # n

        i, iPrev = 0, 0
        while True:
            try:
                i = tmp.index(delim, iPrev)
            except ValueError:
                buf += tmp[iPrev:]
                break
            # except Exception as e:
            #     raise IOError('\n'.join([str(e), tmp, delim]))
            else:
                fp_write(buf + tmp[iPrev:i + len(delim)])
                callback(1)  # n += 1
                buf = ''
                iPrev = i + len(delim)


# ((opt, type), ... )
RE_OPTS = re.compile(r'\n {8}(\S+)\s{2,}:\s*([^\s,]+)')
# better split method assuming no positional args
RE_SHLEX = re.compile(r'\s*--?([^\s=]+)(?:\s*|=|$)')

# TODO: add custom support for some of the following?
UNSUPPORTED_OPTS = ('iterable', 'gui', 'out', 'file')

# The 8 leading spaces are required for consistency
CLI_EXTRA_DOC = r"""
        Extra CLI Options
        -----------------
        delim  : chr, optional
            Delimiting character [default: '\n']. Use '\0' for null.
            N.B.: on Windows systems, Python converts '\n' to '\r\n'.
        buf_size  : int, optional
            String buffer size in bytes [default: 256]
            used when `delim` is specified.
"""


def main():
    d = tqdm.__init__.__doc__ + CLI_EXTRA_DOC

    opt_types = dict(RE_OPTS.findall(d))

    for o in UNSUPPORTED_OPTS:
        opt_types.pop(o)

    # d = RE_OPTS.sub(r'  --\1=<\1>  : \2', d)
    split = RE_OPTS.split(d)
    opt_types_desc = zip(split[1::3], split[2::3], split[3::3])
    d = ''.join('\n  --{0}=<{0}>  : {1}{2}'.format(*otd)
                for otd in opt_types_desc if otd[0] not in UNSUPPORTED_OPTS)

    __doc__ = """Usage:
  tqdm [--help | options]

Options:
  -h, --help     Print this help and exit
  -v, --version  Print version and exit

""" + d.strip('\n') + '\n'

    # opts = docopt(__doc__, version=__version__)
    if any(v in sys.argv for v in ('-v', '--version')):
        sys.stdout.write(__version__ + '\n')
        sys.exit(0)
    elif any(v in sys.argv for v in ('-h', '--help')):
        sys.stdout.write(__doc__ + '\n')
        sys.exit(0)

    argv = RE_SHLEX.split('tqdm ' + ' '.join(sys.argv[1:]))
    opts = dict(zip(argv[1::2], argv[2::2]))

    tqdm_args = {}
    # try:
    #     dumb_stdin = os.fdopen(sys.stdin.fileno(), "rb", 0)
    #     dumb_stdout = os.fdopen(sys.stdout.fileno(), "wb", 0)
    # except Exception as e:
    #     if 'fileno' not in str(e):
    #         posix_pipe(dumb_stdin, dumb_stdout, '\n')
    #         raise
    #     # mock io - probably list or StringIO
    #     dumb_stdin = sys.stdin
    #     dumb_stdout = sys.stdout
    try:
        for (o, v) in opts.items():
            try:
                tqdm_args[o] = cast(v, opt_types[o])
            except KeyError as e:
                raise TqdmKeyError(str(e))
        # sys.stderr.write('\ndebug | args: ' + str(tqdm_args) + '\n')
    except:
        sys.stderr.write('\nError:\nUsage:\n  tqdm [--help | options]\n')
        posix_pipe(sys.stdin, sys.stdout)
        # mock_stdin = os.fdopen(os.dup(sys.stdin.fileno()), "rb") \
        #     if hasattr(sys.stdin, 'fileno') else sys.stdin
        # for i in mock_stdin:
        #     sys.stdout.write(i)
        raise
    else:
        delim = tqdm_args.pop('delim', '\n')
        buf_size = tqdm_args.pop('buf_size', 256)
        with tqdm(**tqdm_args) as t:
            posix_pipe(sys.stdin, sys.stdout,
                       delim, 1 if delim == '\n' else buf_size, t.update)
