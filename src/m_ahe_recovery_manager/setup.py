from setuptools import find_packages, setup

package_name = 'm_ahe_recovery_manager'

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
    description='Event-triggered recovery and replanning manager for AHE-MRTA',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # Phase 8: recovery_manager_node = m_ahe_recovery_manager.recovery_manager_node:main
        ],
    },
)
