from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="document-assembly-tool",
    version="2.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Enterprise document assembly: merge structured data into Word templates with full formatting preservation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/PC-User-Guest/document-assembly-tool",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Legal Industry",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.10",
        "Topic :: Office/Business",
        "Topic :: Text Processing"
    ],
    python_requires=">=3.10",
    install_requires=[
        "python-docx>=0.8.10",
    ],
    entry_points={
        "console_scripts": [
            "doc-assemble=src.document_assembler:main",
        ],
    },
)
