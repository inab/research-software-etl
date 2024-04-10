# Integrating Use Cases with GitLab CI via CLI Adapters

## Overview

This guide provides instructions for contributors on how to integrate application use cases with GitLab CI/CD pipelines using Command Line Interface (CLI) adapters. Following a clean architecture, our application separates core business logic (use cases) from external interfaces (adapters), ensuring modularity and maintainability.

## Prerequisites

- Familiarity with Python programming.
- Basic understanding of clean architecture principles.
- Access to the project's GitLab repository.

## Examples 
The following use cases are currently automated with GitLab CI via CLI adapters:

- **Data Transformation**: Use cases that transform data from a source-specific format to the common format.
- **Data Integration**: Use cases that integrate data from multiple sources into a unified dataset.

## Step 1: Understanding Use Cases

Use cases encapsulate specific business logic in our application. Each use case should have a clearly defined purpose, inputs, and outputs. If you're adding a new feature, define its business logic as a use case.

## Step 2: Writing a CLI Adapter

1. **Create the Adapter File**: Inside the `adapters/cli` directory, create a Python file for your CLI adapter, e.g., `my_feature_cli.py`.
2. **Implement Argument Parsing**: Use the `argparse` library to define how to pass arguments to your script from the command line. These arguments will typically correspond to the inputs of your use case.
3. **Trigger the Use Case**: Within the adapter, instantiate and execute your use case, passing the necessary arguments.

Example CLI Adapter (`adapters/cli/my_feature_cli.py`):

```python
import argparse
from use_cases.my_feature_use_case import MyFeatureUseCase

def main():
    parser = argparse.ArgumentParser(description="Description of what my feature does.")
    parser.add_argument('--example_arg', type=str, help='An example argument.')

    args = parser.parse_args()

    use_case = MyFeatureUseCase()
    use_case.execute(example_arg=args.example_arg)

if __name__ == "__main__":
    main()
```

## Step 3: Modify GitLab CI Configuration

1. Open the `.gitlab-ci.yml` file at the root of your project.
2. Add a new job under the `script` section to execute your CLI adapter. Specify any necessary environment variables or prerequisites.

Example GitLab CI job:

```yaml
my_feature_job:
  stage: my_feature_stage
  script:
    - python adapters/cli/my_feature_cli.py --example_arg "value"
  only:
    - master
```

## Step 4: Test Your Integration

Before pushing your changes, test the CLI adapter locally to ensure it works as expected. Then, commit your changes and push them to the repository. Monitor the GitLab CI/CD pipeline to ensure your new job executes successfully.

## Additional Guidelines

- **Security**: Handle sensitive information securely, especially when passing it through GitLab CI/CD environments.
- **Documentation**: Clearly document your CLI adapter and its arguments to assist other contributors.
- **Collaboration**: Review existing adapters and use cases for examples and consistency in implementation.

