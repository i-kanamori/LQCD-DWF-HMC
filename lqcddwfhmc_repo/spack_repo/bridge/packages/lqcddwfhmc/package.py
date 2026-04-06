# Copyright Spack Project Developers. See COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack_repo.builtin.build_systems.makefile import MakefilePackage
from spack.package import *


class Lqcddwfhmc(MakefilePackage):
    """LQCD-DWF-HMC benchmark for Bridge code for lattice QCD simulations."""

    homepage = "https://bridge.kek.jp/Lattice-code/"
    # url    = "https://bridge.kek.jp/Lattice-code/code/old/bridge-2.1.0.tar.gz"
    git      = "https://github.com/i-kanamori/LQCD-DWF-HMC.git"

    maintainers("i-kanamori", "freifrauvonbleifrei")

    license("GPL-3.0", checked_by="freifrauvonbleifrei")

    version("main", branch="main") # , submodules=True)?

    variant('mpi', default=True, description='Enable MPI support') # , values=('yes', 'no', 'fjmpi')
    variant('gpu', default=False, description='Enable GPU support through OpenACC')
    variant('openmp', default=True, description='Enable OpenMP support')
    variant('opt', default=True, description='Enable optimized code')
    variant('gauge_group', default='su3', values=('su2', 'su3'), multi=False, description='Gauge group')
    variant('testmanager', default=False, description='Enable test manager')
    variant('fftw', default=False, description='Enable FFTW library support')
    variant('doxygen', default=False, description='Enable Doxygen documentation')

    depends_on("cxx", type="build")

    depends_on('mpi', when='+mpi')
    depends_on('fftw@3:', when='+fftw')
    depends_on('fftw+mpi', when='+fftw+mpi')
    depends_on('doxygen', when='+doxygen')

    # OpenACC accelerator code requires the NVIDIA HPC SDK compiler (restrict keyword, OpenACC pragmas)
    requires('%nvhpc', when='+gpu', msg='GPU support via OpenACC requires the NVIDIA HPC SDK compiler (nvhpc)')

    def edit(self, spec, prefix):
        makefile = join_path(self.stage.source_path, 'Makefile')
        filter = FileFilter(makefile)
        
        # Modify existing variables in Makefile: r"^\s* means newline and any leading spaces
        if ('^fujitsu-mpi' in spec and '+mpi' in spec):
            filter.filter(r'^\s*use_mpi =.*', 'use_mpi = fjmpi')
        else:
            filter.filter(r'^\s*use_mpi =.*', 'use_mpi = {0}'.format('yes' if '+mpi' in spec else 'no'))
        filter.filter(r'^\s*use_thread =.*', 'use_thread = {0}'.format('omp' if '+openmp' in spec else 'no'))
        filter.filter(r'^\s*use_opt_code =.*', 'use_opt_code = {0}'.format('yes' if '+opt' in spec else 'no'))
        filter.filter(r'^\s*use_gauge_group =.*', 'use_gauge_group = {0}'.format(spec.variants['gauge_group'].value))
        filter.filter(r'^\s*use_testmanager =.*', 'use_testmanager = {0}'.format('yes' if '+testmanager' in spec else 'no'))
        filter.filter(r'^\s*use_fftw_library =.*', 'use_fftw_library = {0}'.format('yes' if '+fftw' in spec else 'no'))
        filter.filter(r'^\s*use_fftw =.*', 'use_fftw = {0}'.format('yes' if '+fftw' in spec else 'no'))
        filter.filter(r'^\s*fftw_library_path =.*', 'fftw_library_path = {0}'.format(spec['fftw'].prefix if '+fftw' in spec else ''))
        filter.filter(r'^\s*use_alternative =.*', 'use_alternative = yes')
        # filter.filter(r'^\s*use_cpp11 =.*', 'use_cpp11 = yes')
        filter.filter(r'^\s*use_qxs_arch =.*', 'use_qxs_arch = {0}'.format('acle' if spec.target == 'a64fx' else 'general'))
        filter.filter(r'^\s*use_complex =.*', 'use_complex = std')
        # The benchmark executable needs either USE_ALT_QXS or USE_ALT_ACCEL to define IMPL.
        filter.filter(r'^\s*use_alt_qxs =.*', 'use_alt_qxs = {0}'.format('no' if '+gpu' in spec else 'yes'))
        filter.filter(r'^\s*use_alt_accel =.*', 'use_alt_accel = {0}'.format('yes' if "+gpu" in spec else 'no'))
        if '+mpi' in spec:
            filter.filter('CXX =.*', 'CXX = {0}'.format(spec['mpi'].mpicxx))
        
        filter.filter(r'^\s*target =.*', 'target = {0}'.format(
            'Fugaku_CLANG' if spec.target == 'a64fx' else
            # 'SX_AURORA' if spec.target.family == 've' else
            'PC_GNU' if spec["cxx"].name == "gcc" else
            'PC_CLANG' if spec["cxx"].name == "clang" else
            'PC_INTEL' if spec["cxx"].name == "intel" else
            'PC_NVIDIA' if spec["cxx"].name == "nvhpc" else
            'PC_GNU'  # default
        ))     #TODO 've' is not really a thing...

        makefile_target = join_path(self.stage.source_path, 'Makefile_target.inc')
        filter = FileFilter(makefile_target)
        if '+mpi' in spec:
            filter.filter('CXX =.*', 'CXX = {0}'.format(spec['mpi'].mpicxx))

    def build(self, spec, prefix):
        make()
        # build the benchmark executable
        make('-C', 'benchmark_hmc_dwf')

    def install(self, spec, prefix):
        # no install target -> manually copy files
        mkdir(prefix.lib)
        install('build/libbridge.a', prefix.lib + "/libbridge.a")
        install_tree('build/include/bridge/', prefix.include)
        # install the benchmark executable and its parameter files
        mkdirp(prefix.bin)
        install('benchmark_hmc_dwf/hmc_dwf_eo.elf', prefix.bin)
        mkdirp(prefix.share.bridge)
        for f in find('.', 'benchmark_hmc_dwf/*.yaml'):
            install(f, prefix.share.bridge)
