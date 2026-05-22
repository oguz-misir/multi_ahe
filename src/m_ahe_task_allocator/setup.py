from setuptools import find_packages, setup

package_name = 'm_ahe_task_allocator'

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
    description='Task allocator and baseline implementations for AHE-MRTA',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'task_queue_test_pub = m_ahe_task_allocator.task_queue_test_pub:main',
            'baseline_allocator_node = m_ahe_task_allocator.baseline_allocator_node:main',
            'ahe_allocator_node = m_ahe_task_allocator.ahe_allocator_node:main',
            'experiment_runner_node = m_ahe_task_allocator.experiment_runner_node:main',
        ],
    },
)
