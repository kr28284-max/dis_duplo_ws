from setuptools import find_packages, setup

package_name = 'control_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='da',
    maintainer_email='da@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'robot_node = control_pkg.robot_node:main',
            'robot_node_2 = control_pkg.robot_node_2:main',
            'robot_node_3 = control_pkg.robot_node_3:main',
            'master_node_dis = control_pkg.master_node_dis:main',
            'master_node_dis2 = control_pkg.master_node_dis2:main',
            'master_node_dis3 = control_pkg.master_node_dis3:main',
            'master_node_dis4 = control_pkg.master_node_dis4:main',
            'master_node_dis5 = control_pkg.master_node_dis5:main',
            'master_node_dis6 = control_pkg.master_node_dis6:main',
            'master_node_dis7 = control_pkg.master_node_dis7:main',
            'master_node_dis8 = control_pkg.master_node_dis8:main',
            'master_node_dis9 = control_pkg.master_node_dis9:main',
            'master_node_dis10 = control_pkg.master_node_dis10:main',
            'master_node_dis11 = control_pkg.master_node_dis11:main',
            'test_node1 = control_pkg.test_node1:main',
        ],
    },
)
