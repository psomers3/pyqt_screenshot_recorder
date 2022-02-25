from distutils.core import setup

include_package_data = False

setup(name='screenshot_recorder',
      version='1.0',
      description='PyQt Window for extracting screenshots from a video',
      author='Peter Somers',
      author_email='peter.somers@isys.uni-stuttgart.de',
      url='https://github.com/psomers3/pyqt_screenshot_recorder',
      packages=['screenshot_recorder'],
      package_data={'screenshot_recorder': ['ffmpeg/*exe']},
      include_package_data=include_package_data
     )