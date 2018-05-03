import setuptools


setuptools.setup(
    name="geekie-kamikaze-agent",
    version="1.0.0",
    url="https://github.com/projetoeureka/kamikaze-agent",
    maintainer="Geekie",
    maintainer_email="sherman@geekie.com.br",
    packages=["kamikaze"],
    include_package_data=True,
    zip_safe=False,
    setup_requires=["setuptools_git==1.0b1"],
    install_requires=[
        "requests>=2",
    ],
)
