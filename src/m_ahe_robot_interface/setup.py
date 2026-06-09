from setuptools import find_packages, setup

package_name = 'm_ahe_robot_interface'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='AHE-MRTA Team',
    maintainer_email='dr.oguz.misir@gmail.com',
    description='Robot interface and Nav2 action client for AHE-MRTA',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'robot_interface_node = m_ahe_robot_interface.robot_interface_node:main',
        ],
    },
)
