project('sysdupd',
  version: '0.1.0',
  license: 'GPL3',
  meson_version: '>=0.60.0'
)

python = import('python').find_installation('python3')
gnome = import('gnome')

# installation paths
prefix = get_option('prefix')
bindir = get_option('bindir')
datadir = get_option('datadir')
pkgdatadir = join_paths(datadir, meson.project_name())
python_dir = python.get_install_dir()

# compile gresources
sysdupd_gresource = gnome.compile_resources('sysdupd-resources',
  'data/resources.gresource.xml',
  source_dir: 'data',
  gresource_bundle: true, # this is the magic flag for python
  install: true,
  install_dir: pkgdatadir,
)

# install python source
install_subdir('sysdupd', 
  install_dir: python_dir,
)

# create the launcher script
conf = configuration_data()
conf.set('PYTHON', python.full_path())
conf.set('VERSION', meson.project_version())
conf.set('pkgdatadir', pkgdatadir)
conf.set('python_dir', python_dir)

configure_file(
  input: 'data/sysdupd.in',
  output: 'sysdupd',
  configuration: conf,
  install_dir: bindir,
  install_mode: 'rwxr-xr-x'
)

# schemas and desktop files
install_data('data/com.virex.Sysdupd.gschema.xml',
  install_dir: join_paths(datadir, 'glib-2.0/schemas')
)
gnome.compile_schemas()

install_data('data/com.virex.Sysdupd.policy',
  install_dir: '/usr/share/polkit-1/actions'
)

install_data('data/com.virex.Sysdupd.desktop',
  install_dir: join_paths(datadir, 'applications')
)

install_data('data/com.virex.Sysdupd.appdata.xml',
  install_dir: join_paths(datadir, 'metainfo')
)