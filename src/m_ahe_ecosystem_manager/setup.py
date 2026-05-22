from setuptools import find_packages, setup

package_name = 'm_ahe_ecosystem_manager'

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
    description='AHE ecosystem manager: context vector, dominance, cooperation, suppression, weights',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'ecosystem_test_pub = m_ahe_ecosystem_manager.ecosystem_test_pub:main',
            'ecosystem_manager_node = m_ahe_ecosystem_manager.ecosystem_manager_node:main',
        ],
    },
)
