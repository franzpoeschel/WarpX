# --- This defines the wrapper functions that directly call the underlying compiled routines
import os
import sys
import ctypes
from ctypes.util import find_library
import numpy as np
from numpy.ctypeslib import ndpointer


def get_package_root():
    '''
    Get the path to the installation location (where libwarpx.so would be installed).
    '''
    cur = os.path.abspath(__file__)
    while True:
        name = os.path.basename(cur)
        if name == 'pywarpx':
            return cur
        elif not name:
            return ''
        cur = os.path.dirname(cur)

libwarpx = ctypes.CDLL(os.path.join(get_package_root(), "libwarpx.so"))
libc = ctypes.CDLL(find_library('c'))



libwarpx.warpx_getistep.restype = ctypes.c_int
libwarpx.warpx_gett_new.restype = ctypes.c_double
libwarpx.warpx_getdt.restype = ctypes.c_double
libwarpx.warpx_maxStep.restype = ctypes.c_int
libwarpx.warpx_stopTime.restype = ctypes.c_double
libwarpx.warpx_checkInt.restype = ctypes.c_int
libwarpx.warpx_plotInt.restype = ctypes.c_int
libwarpx.warpx_finestLevel.restype = ctypes.c_int


libwarpx.warpx_EvolveE.argtypes = [ctypes.c_int, ctypes.c_double]
libwarpx.warpx_EvolveB.argtypes = [ctypes.c_int, ctypes.c_double]
libwarpx.warpx_FillBoundaryE.argtypes = [ctypes.c_int, ctypes.c_bool]
libwarpx.warpx_FillBoundaryB.argtypes = [ctypes.c_int, ctypes.c_bool]
libwarpx.warpx_PushParticlesandDepose.argtypes = [ctypes.c_int, ctypes.c_double]
libwarpx.warpx_getistep.argtypes = [ctypes.c_int]
libwarpx.warpx_setistep.argtypes = [ctypes.c_int, ctypes.c_int]
libwarpx.warpx_gett_new.argtypes = [ctypes.c_int]
libwarpx.warpx_sett_new.argtypes = [ctypes.c_int, ctypes.c_double]
libwarpx.warpx_getdt.argtypes = [ctypes.c_int]



# some useful data structures and typenames
class Particle(ctypes.Structure):
    _fields_ = [('x', ctypes.c_double),
                ('y', ctypes.c_double),
                ('z', ctypes.c_double),
                ('id', ctypes.c_int),
                ('cpu', ctypes.c_int)]


p_dtype = np.dtype([('x', 'f8'), ('y', 'f8'), ('z', 'f8'),
                    ('id', 'i4'), ('cpu', 'i4')])

c_double_p = ctypes.POINTER(ctypes.c_double)
LP_c_char = ctypes.POINTER(ctypes.c_char)
LP_LP_c_char = ctypes.POINTER(LP_c_char)

# where do I import these? this might only work for CPython...
PyBuf_READ  = 0x100
PyBUF_WRITE = 0x200

# this is a function for converting a ctypes pointer to a numpy array    
def array1d_from_pointer(pointer, dtype, size):
    if sys.version_info.major >= 3:
        buffer_from_memory = ctypes.pythonapi.PyMemoryView_FromMemory
        buffer_from_memory.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_int)
        buffer_from_memory.restype = ctypes.py_object
        buf = buffer_from_memory(pointer, dtype.itemsize*size, PyBUF_WRITE)
    else:        
        buffer_from_memory = ctypes.pythonapi.PyBuffer_FromReadWriteMemory
        buffer_from_memory.restype = ctypes.py_object
        buf = buffer_from_memory(pointer, dtype.itemsize*size)
    return np.frombuffer(buf, dtype=dtype, count=size)
    

# set the arg and return types of the wrapped functions
f = libwarpx.amrex_init
f.argtypes = (ctypes.c_int, LP_LP_c_char)

f = libwarpx.warpx_getParticleStructs
f.restype = ctypes.POINTER(ctypes.POINTER(Particle))

f = libwarpx.warpx_getParticleArrays
f.restype = ctypes.POINTER(c_double_p)

f = libwarpx.warpx_getParticleArrays
f.restype = ctypes.POINTER(c_double_p)

f = libwarpx.warpx_getEfield
f.restype = ctypes.POINTER(c_double_p)

f = libwarpx.warpx_getBfield
f.restype = ctypes.POINTER(c_double_p)

f = libwarpx.warpx_getCurrentDensity
f.restype = ctypes.POINTER(c_double_p)

f = libwarpx.addNParticles
f.argtypes = (ctypes.c_int, ctypes.c_int,
              ndpointer(ctypes.c_double, flags="C_CONTIGUOUS"), 
              ndpointer(ctypes.c_double, flags="C_CONTIGUOUS"),
              ndpointer(ctypes.c_double, flags="C_CONTIGUOUS"),
              ndpointer(ctypes.c_double, flags="C_CONTIGUOUS"),
              ndpointer(ctypes.c_double, flags="C_CONTIGUOUS"),
              ndpointer(ctypes.c_double, flags="C_CONTIGUOUS"),
              ctypes.c_int,
              ndpointer(ctypes.c_double, flags="C_CONTIGUOUS"),
              ctypes.c_int)

def amrex_init(argv):
    # --- Construct the ctype list of strings to pass in
    argc = len(argv)
    argvC = (LP_c_char * (argc+1))()
    for i, arg in enumerate(argv):
        enc_arg = arg.encode('utf-8')
        argvC[i] = ctypes.create_string_buffer(enc_arg)

    libwarpx.amrex_init(argc, argvC)

def add_particles(species_number,
                  x, y, z, ux, uy, uz, attr, unique_particles):
    '''

    A function for adding particles to the WarpX simulation.

    Parameters
    ----------

        species_number   : the species to add the particle to
        x, y, z          : numpy arrays of the particle positions
        ux, uy, uz       : numpy arrays of the particle momenta
        attr             : a 2D numpy array with the particle attributes
        unique_particles : whether the particles are unique or duplicated on 
                           several processes

    '''
    libwarpx.addNParticles(species_number, x.size,
                           x, y, z, ux, uy, uz,
                           attr.shape[1], attr, unique_particles)

def get_particle_structs(species_number):
    '''
    
    This returns a list of numpy arrays containing the particle struct data
    on each tile for this process. The particle data is represented as a structured 
    numpy array and contains the particle 'x', 'y', 'z', 'id', and 'cpu'. 

    The data for the numpy arrays are not copied, but share the underlying 
    memory buffer with WarpX. The numpy arrays are fully writeable.

    Parameters
    ----------

        species_number : the species id that the data will be returned for

    Returns
    -------

        A List of numpy arrays.

    '''

    particles_per_tile = ctypes.POINTER(ctypes.c_int)()
    num_tiles = ctypes.c_int(0)
    data = libwarpx.warpx_getParticleStructs(0, ctypes.byref(num_tiles),
                                             ctypes.byref(particles_per_tile))

    particle_data = []
    for i in range(num_tiles.value):
        arr = array1d_from_pointer(data[i], p_dtype, particles_per_tile[i])
        particle_data.append(arr)

    libc.free(particles_per_tile)
    libc.free(data)
    return particle_data


def get_particle_arrays(species_number, comp):
    '''
   
    This returns a list of numpy arrays containing the particle array data
    on each tile for this process.

    The data for the numpy arrays are not copied, but share the underlying 
    memory buffer with WarpX. The numpy arrays are fully writeable.

    Parameters
    ----------

        species_number : the species id that the data will be returned for
        comp           : the component of the array data that will be returned.

    Returns
    -------

        A List of numpy arrays.
    
    '''
    
    particles_per_tile = ctypes.POINTER(ctypes.c_int)()
    num_tiles = ctypes.c_int(0)
    data = libwarpx.warpx_getParticleArrays(0, comp, ctypes.byref(num_tiles),
                                            ctypes.byref(particles_per_tile))

    particle_data = []
    for i in range(num_tiles.value):
        arr = np.ctypeslib.as_array(data[i], (particles_per_tile[i],))
        arr.setflags(write=1)
        particle_data.append(arr)

    libc.free(particles_per_tile)
    libc.free(data)
    return particle_data


def get_particle_x(species_number):
    '''

    Return a list of numpy arrays containing the particle 'x'
    positions on each tile.

    '''
    structs = get_particle_structs(species_number)
    return [struct['x'] for struct in structs]


def get_particle_y(species_number):
    '''

    Return a list of numpy arrays containing the particle 'y'
    positions on each tile.

    '''
    structs = get_particle_structs(species_number)
    return [struct['y'] for struct in structs]


def get_particle_z(species_number):
    '''

    Return a list of numpy arrays containing the particle 'z'
    positions on each tile.

    '''
    structs = get_particle_structs(species_number)
    return [struct['z'] for struct in structs]


def get_particle_id(species_number):
    '''

    Return a list of numpy arrays containing the particle 'z'
    positions on each tile.

    '''
    structs = get_particle_structs(species_number)
    return [struct['id'] for struct in structs]


def get_particle_cpu(species_number):
    '''

    Return a list of numpy arrays containing the particle 'z'
    positions on each tile.

    '''
    structs = get_particle_structs(species_number)
    return [struct['cpu'] for struct in structs]


def get_particle_weight(species_number):
    '''

    Return a list of numpy arrays containing the particle
    weight on each tile.

    '''

    return get_particle_arrays(species_number, 0)


def get_particle_ux(species_number):
    '''

    Return a list of numpy arrays containing the particle
    x momentum on each tile.

    '''

    return get_particle_arrays(species_number, 1)


def get_particle_uy(species_number):
    '''

    Return a list of numpy arrays containing the particle
    y momentum on each tile.

    '''

    return get_particle_arrays(species_number, 2)


def get_particle_uz(species_number):
    '''

    Return a list of numpy arrays containing the particle
    z momentum on each tile.

    '''

    return get_particle_arrays(species_number, 3)


def get_particle_Ex(species_number):
    '''

    Return a list of numpy arrays containing the particle
    x electric field on each tile.

    '''

    return get_particle_arrays(species_number, 4)


def get_particle_Ey(species_number):
    '''

    Return a list of numpy arrays containing the particle
    y electric field on each tile.

    '''

    return get_particle_arrays(species_number, 5)


def get_particle_Ez(species_number):
    '''

    Return a list of numpy arrays containing the particle
    z electric field on each tile.

    '''

    return get_particle_arrays(species_number, 6)


def get_particle_Bx(species_number):
    '''

    Return a list of numpy arrays containing the particle
    x magnetic field on each tile.

    '''

    return get_particle_arrays(species_number, 7)


def get_particle_By(species_number):
    '''

    Return a list of numpy arrays containing the particle
    y magnetic field on each tile.

    '''

    return get_particle_arrays(species_number, 8)


def get_particle_Bz(species_number):
    '''

    Return a list of numpy arrays containing the particle
    z magnetic field on each tile.

    '''

    return get_particle_arrays(species_number, 9)


def get_mesh_electric_field(level, direction, include_ghosts=True):
    '''
   
    This returns a list of numpy arrays containing the mesh electric field
    data on each grid for this process.

    The data for the numpy arrays are not copied, but share the underlying 
    memory buffer with WarpX. The numpy arrays are fully writeable.

    Parameters
    ----------

        level          : the AMR level to get the data for
        direction      : the component of the data you want
        include_ghosts : whether to include ghost zones or not

    Returns
    -------

        A List of numpy arrays.
    
    '''

    shapes = ctypes.POINTER(ctypes.c_int)()
    size = ctypes.c_int(0)
    ngrow = ctypes.c_int(0)
    data = libwarpx.warpx_getEfield(0, direction,
                                    ctypes.byref(size), ctypes.byref(ngrow), 
                                    ctypes.byref(shapes))
    ng = ngrow.value
    grid_data = []
    for i in range(size.value):
        shape=(shapes[3*i+0], shapes[3*i+1], shapes[3*i+2])
        arr = np.ctypeslib.as_array(data[i], shape)
        arr.setflags(write=1)
        if include_ghosts:
            grid_data.append(arr)
        else:
            grid_data.append(arr[ng:-ng,ng:-ng,ng:-ng])

    libc.free(shapes)
    libc.free(data)
    return grid_data


def get_mesh_magnetic_field(level, direction, include_ghosts=True):
    '''
   
    This returns a list of numpy arrays containing the mesh magnetic field
    data on each grid for this process.

    The data for the numpy arrays are not copied, but share the underlying 
    memory buffer with WarpX. The numpy arrays are fully writeable.

    Parameters
    ----------

        level          : the AMR level to get the data for
        direction      : the component of the data you want
        include_ghosts : whether to include ghost zones or not

    Returns
    -------

        A List of numpy arrays.
    
    '''

    shapes = ctypes.POINTER(ctypes.c_int)()
    size = ctypes.c_int(0)
    ngrow = ctypes.c_int(0)
    data = libwarpx.warpx_getBfield(0, direction,
                                    ctypes.byref(size), ctypes.byref(ngrow), 
                                    ctypes.byref(shapes))
    ng = ngrow.value
    grid_data = []
    for i in range(size.value):
        shape=(shapes[3*i+0], shapes[3*i+1], shapes[3*i+2])
        arr = np.ctypeslib.as_array(data[i], shape)
        arr.setflags(write=1)
        if include_ghosts:
            grid_data.append(arr)
        else:
            grid_data.append(arr[ng:-ng,ng:-ng,ng:-ng])

    libc.free(shapes)
    libc.free(data)
    return grid_data


def get_mesh_current_density(level, direction, include_ghosts=True):
    '''
   
    This returns a list of numpy arrays containing the mesh current density
    data on each grid for this process.

    The data for the numpy arrays are not copied, but share the underlying 
    memory buffer with WarpX. The numpy arrays are fully writeable.

    Parameters
    ----------

        level          : the AMR level to get the data for
        direction      : the component of the data you want
        include_ghosts : whether to include ghost zones or not

    Returns
    -------

        A List of numpy arrays.
    
    '''

    shapes = ctypes.POINTER(ctypes.c_int)()
    size = ctypes.c_int(0)
    ngrow = ctypes.c_int(0)
    data = libwarpx.warpx_getCurrentDensity(0, direction,
                                            ctypes.byref(size), ctypes.byref(ngrow), 
                                            ctypes.byref(shapes))
    ng = ngrow.value
    grid_data = []
    for i in range(size.value):
        shape=(shapes[3*i+0], shapes[3*i+1], shapes[3*i+2])
        arr = np.ctypeslib.as_array(data[i], shape)
        arr.setflags(write=1)
        if include_ghosts:
            grid_data.append(arr)
        else:
            grid_data.append(arr[ng:-ng,ng:-ng,ng:-ng])

    libc.free(shapes)
    libc.free(data)
    return grid_data


