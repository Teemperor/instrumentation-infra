import os
import shutil
import logging
from contextlib import redirect_stdout
from ...util import run, apply_patch, qjoin, FatalError
from ...target import Target


class SPEC2006(Target):
    name = 'spec2006'

    def __init__(self, specdir=None, giturl=None, patches=[]):
        if not specdir and not giturl:
            raise FatalError('should specify one of specdir or giturl')

        if specdir and giturl:
            raise FatalError('cannot specify specdir AND giturl')

        self.specdir = specdir
        self.giturl = giturl
        self.patches = patches

    def add_build_args(self, parser):
        parser.add_argument('--spec2006-benchmarks',
                nargs='+', metavar='BENCHMARK', default=['c', 'c++'],
                choices=list(self.benchmarks.keys()),
                help='which SPEC2006 benchmarks to build')

    def is_fetched(self, ctx):
        return os.path.exists('install/shrc')

    def fetch(self, ctx):
        if self.giturl:
            ctx.log.debug('cloning SPEC2006 repo')
            run(ctx, ['git', 'clone', '--depth', 1, self.giturl, 'src'])
            os.chdir('src')
        else:
            os.chdir(self.specdir)

        install_path = self.path(ctx, 'install')
        ctx.log.debug('installing SPEC2006 into ' + install_path)
        run(ctx, ['./install.sh', '-f', '-d', install_path],
            env={'PERL_TEST_NUMCONVERTS': 1})

        if self.giturl:
            ctx.log.debug('removing cloned SPEC2006 repo to save disk space')
            shutil.rmtree(self.path(ctx, 'src'))

    def build(self, ctx, instance):
        # apply any pending patches (doing this at build time allows adding
        # patches during instance development)
        os.chdir('install')
        config_path = os.path.dirname(os.path.abspath(__file__))
        for path in self.patches:
            if '/' not in path:
                path = '%s/%s.patch' % (config_path, path)
            apply_patch(ctx, path, 1)
        os.chdir('..')

        config = self.make_spec_config(ctx, instance)
        print_output = ctx.loglevel == logging.DEBUG

        benchmarks = []
        for bset in ctx.args.spec2006_benchmarks:
            benchmarks += self.benchmarks[bset]
        benchmarks.sort()

        for bench in benchmarks:
            ctx.log.info('building %s-%s %s' % (self.name, instance.name, bench))
            self.runspec(ctx, config, 'build', bench, teeout=print_output)

    def runspec(self, ctx, config, action, *args, **kwargs):
        config_path = os.path.dirname(os.path.abspath(__file__))
        run(ctx, [
            'bash', '-c',
            'cd %s/install;'
            'source shrc;'
            'source "%s/scripts/kill-tree-on-interrupt.inc";'
            'killwrap_tree runspec --config="%s" --action=%s %s' %
            (self.path(ctx), config_path, config, action, qjoin(args))
        ], **kwargs)

    def make_spec_config(self, ctx, instance):
        config_name = 'infra-' + instance.name
        config_path = self.path(ctx, 'install/config/%s.cfg' % config_name)
        ctx.log.debug('writing SPEC2006 config to ' + config_path)

        with open(config_path, 'w') as f:
            with redirect_stdout(f):
                print('tune        = base')
                print('ext         = ' + config_name)
                print('reportable  = no')
                print('teeout      = yes')
                print('teerunout   = no')
                print('makeflags   = -j%d' % ctx.jobs)
                print('strict_rundir_verify = no')
                print('')
                print('default=default=default=default:')

                # see https://www.spec.org/cpu2006/Docs/makevars.html#nofbno1
                # for flags ordering
                cflags = qjoin(ctx.cflags)
                cxxflags = qjoin(ctx.cxxflags)
                ldflags = qjoin(ctx.ldflags)
                print('CC          = %s %s' % (ctx.cc, cflags))
                print('CXX         = %s %s' % (ctx.cxx, cxxflags))
                print('FC          = `which false`')
                print('CLD         = %s %s' % (ctx.cc, ldflags))
                print('CXXLD       = %s %s' % (ctx.cxx, ldflags))
                print('COPTIMIZE   = -std=gnu89')
                # fix __float128 error in clang:
                print('CXXPORTABILITY = -D__STRICT_ANSI__')

                # post-build hooks call back into the setup script
                if ctx.hooks.post_build:
                    print('')
                    print('build_post_bench = %s exec-hook post-build %s '
                        '`echo ${commandexe} | sed "s/_\\[a-z0-9\\]\\\\+\\\\.%s\\\\\\$//"`' %
                        (ctx.paths.setup, instance.name, config_name))
                    print('')

                if 'target_run_wrapper' in ctx:
                    print('')
                    print('monitor_wrapper = %s \$command' % ctx.target_run_wrapper)

                # configure benchmarks for 64-bit Linux (hardcoded for now)
                print('')
                print('default=base=default=default:')
                print('PORTABILITY    = -DSPEC_CPU_LP64')
                print('')
                print('400.perlbench=default=default=default:')
                print('CPORTABILITY   = -DSPEC_CPU_LINUX_X64')
                print('')
                print('462.libquantum=default=default=default:')
                print('CPORTABILITY   = -DSPEC_CPU_LINUX')
                print('')
                print('483.xalancbmk=default=default=default:')
                print('CXXPORTABILITY = -DSPEC_CPU_LINUX')
                print('')
                print('481.wrf=default=default=default:')
                print('wrf_data_header_size = 8')
                print('CPORTABILITY   = -DSPEC_CPU_CASE_FLAG -DSPEC_CPU_LINUX')

        return config_name

    def link(self, ctx, instance):
        pass

    # override post-build hook runner rather than defining `binary_paths` since
    # we add hooks to the generated SPEC config file and call them through the
    # exec-hook setup command instead
    def run_hooks_post_build(self, ctx, instance):
        pass

    # define benchmark sets
    benchmarks = {
        'int': [
            '400.perlbench',
            '401.bzip2',
            '403.gcc',
            '429.mcf',
            '445.gobmk',
            '456.hmmer',
            '458.sjeng',
            '462.libquantum',
            '464.h264ref',
            '471.omnetpp',
            '473.astar',
            '483.xalancbmk'
        ],
        'fp': [
            '410.bwaves',
            '416.gamess',
            '433.milc',
            '434.zeusmp',
            '435.gromacs',
            '436.cactusADM',
            '437.leslie3d',
            '444.namd',
            '447.dealII',
            '450.soplex',
            '453.povray',
            '454.calculix',
            '459.GemsFDTD',
            '465.tonto',
            '470.lbm',
            '481.wrf',
            '482.sphinx3'
        ],
        'c': [
            '400.perlbench',
            '401.bzip2',
            '403.gcc',
            '429.mcf',
            '433.milc',
            '445.gobmk',
            '456.hmmer',
            '458.sjeng',
            '462.libquantum',
            '464.h264ref',
            '470.lbm',
            '482.sphinx3'
        ],
        'c++': [
            '444.namd',
            '447.dealII',
            '450.soplex',
            '453.povray',
            '471.omnetpp',
            '473.astar',
            '483.xalancbmk'
        ],
        'fortran': [
            '410.bwaves',
            '416.gamess',
            '434.zeusmp',
            '435.gromacs',
            '436.cactusADM',
            '437.leslie3d',
            '454.calculix',
            '459.GemsFDTD',
            '465.tonto',
            '481.wrf'
        ]
    }
    benchmarks['all'] = sorted(benchmarks['int'] + benchmarks['fp'])
    for bench in benchmarks['all']:
        benchmarks[bench] = [bench]
