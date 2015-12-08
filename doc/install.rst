Installation Instructions
=========================

OpenModes is a package for the `Python <http://www.python.org/>`_ language, and the
instructions here include the easiest way to install it.

Quick Install Instructions
--------------------------

1. Download the **64 bit** version of the `Anaconda`_ 
   python distribution, which includes all the required python 
   libraries.
  
   You can install Anaconda without administrator access, and
   it is available for Windows, Linux and Mac OSX.
   
   Python 3.5 is recommended, and Python 2.7 will continue to be supported.

2. Install `gmsh`_ **version 2.8.4 or later**

3. Ensure that the location of the gmsh executable is added to the
   PATH environment variable, so running the following on the command-line
   does not give an error:

   ``gmsh --version``
   
4. From the anaconda command-line, OpenModes can be installed with the command 

   ``pip install openmodes``.

If installation was successful, the next step is to try the examples, see the :doc:`getting started <gettingstarted>` section.

Upgrading to a Newer Version
----------------------------

It's usually a good idea to update all your other Python packages first with

    ``conda update --all``

You can upgrade your installed version from the command-line, using the command

    ``pip install --upgrade --no-deps openmodes``
   
Detailed Requirements
---------------------
The following software packages are the absolute minimum to run OpenModes:

- python 2.7, or any version after 3.3
- numpy (1.6.2 or later)
- scipy
- `gmsh`_ (2.8.4 or later)
- matplotlib (or some other package to plot the results)

Strongly recommended packages

- IPython (the notebook is used by many of the examples, and it allows inline 3D plots)
- jinja2 (for 3D plots in the notebook)
- `Mayavi`_ (to export 3D plots to vtk file format, or to directly view the results)
- ViSit or `ParaView`_ (3D plotting software to view vtk files)

Other packages which may be useful

- spyder (a GUI for editing python)

OpenModes contains some core routines which are optimised using fortran.
Therefore, on platforms where a binary package of OpenModes is not provided,
a fortran compiler is required.

For windows users, there are several choices of scientific python distribution
which may be suitable

- WinPython
- `Anaconda`_
- Enthought Python Distribution
- Enthought Canopy

Compiling yourself under windows is quite difficult, due to incompatibility
of the freely available fortran compilers with windows, particularly under 64 bit.
The pre-compiled versions were created with Microsoft C compilers and Intel
Fortran compiler.

Ubuntu Linux
------------

Most Linux distributions come with python and most of the required libraries. 
For ubuntu users, the appropriate packages can be installed using the following
command

``sudo apt-get install python python-numpy python-matplotlib gmsh gfortran
ipython python-dev python-mayavi python-pip``

OpenModes itself can then be installed using the command

``sudo pip install OpenModes``

If you don't have root access to your Linux machine, then use the command

``pip install --user OpenModes``

Alternatively, the `Anaconda`_ distribution can be used just as under Windows

Note that due to a bug in numpy, compilation may fail under Python 3.x. This is fixed
in numpy's master repository, but your Linux distribution probably has an older release of numpy.
The fix is relatively simple to apply to your own local copy of numpy, see the 
`github pull request <https://github.com/numpy/numpy/pull/5638>`_.

Mac OSX
-------

This code has not been tested for Mac OSX, but there is no known reason why it should
not work. All required packages should be available from the MacPorts project, or
by installing Anaconda.

Manual Install for Windows
--------------------------

Manual installation under windows is difficult, therefore it is recommended to use the
pre-compiled binaries. Compilation requires the use of 
mingw32 or mingw64 compilers, as these are the only free Fortran compilers available for
windows. Unfortunately the default setting on most systems will not successfully
compile the required libraries.

As of version 4.8 and possibly earlier, Mingw32/64 have a bug which causes the
fortran extensions to randomly generate NaNs in the returned arrays if
optimisation levels -O2 or -O3 are specified, therefore the default optimisation
level has been set to -O1.

Previously 32 bit windows binaries were successfully built under the mingw-64 
x32-4.8.1-posix-dwarf-rev5 compiler. For 64 bit windows, binaries were successfully
build using the x64-4.8.1-posix-seh-rev5 compiler. Both were installed using the
`mingw-builds <http://sourceforge.net/projects/mingwbuilds/>`_ installer.

In order for setup.py to find these compilers, they must be in the path. To be safe,
ensure that no other C or fortran compilers are in the path. Python's distutils
must be instructed to use the mingw32 compiler (for both 32 or 64 bit), using the
``--compiler flag``, or by editing the file ``Lib/site-packages/distutils/distutils.cfg``
under your python installation.

In addition, for 64 bit versions, it is necessary to replace the line
``raise NotImplementedError("Only MS compiler supported with gfortran on win64")`` with 
``pass`` in the file ``Lib/site-packages/numpy/distutils/fcompiler/gnu.py``.

Downloading the Source
----------------------
The source is available on `GitHub <https://github.com/DavidPowell/OpenModes>`_

Building the Documentation
--------------------------

In order to build the documentation, the following packages are required

- numpydoc
- Sphinx
- pandoc

At a system command prompt, enter the ``doc`` directory and type ``make html``.

.. _Anaconda: http://docs.continuum.io/anaconda/install.html
.. _gmsh: http://geuz.org/gmsh/
.. _mayavi: http://docs.enthought.com/mayavi/mayavi/
.. _Paraview: http://www.paraview.org/
