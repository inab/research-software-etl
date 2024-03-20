# Architecture Overview 

## Clean Architecture 

### Overview

"Clean Architecture" is a concept within software engineering that focuses on the design and organization of code in a way that promotes maintainability, scalability, and the independence of the system's business rules from UIs, frameworks, and databases. This architecture was popularized by Robert C. Martin (Uncle Bob) in his book "Clean Architecture: A Craftsman's Guide to Software Structure and Design." 

![./static/clean_arch.png](./static/clean_arch.png)

Here’s a concise summary of its core principles:

### Components of Clean Architecture

- **Entities**: These are the business objects of the application. They encapsulate the most general and high-level rules. Entities are the least likely to change when something external changes. For example, the method of calculating a loan's interest rate might change, but the concept of a loan does not.

- **Use Cases**: The application's business rules. Use cases orchestrate the flow of data to and from the entities, and direct those entities to use their enterprise-wide business rules to achieve the goals of the use case.

- **Interface Adapters**: This layer converts data from the format most convenient for the use cases and entities, to the format most convenient for some external agency such as a database or the web. It includes things like Controllers, Gateways, and Presenters.

- **Frameworks and Drivers**: The outermost layer of the architecture. It consists of frameworks and tools such as the Database, the Web Framework, etc. Generally, you do not write much code in this layer other than glue code that communicates to the next circle inwards.

Aditionally, we have: 

- **Configuration**: Manages configuration settings and environment-specific variables, helping to keep the application adaptable and easier to configure across different environments.
    
- **Tests**: The project's test suite, mirroring the structure of the application code to make it easier to maintain and understand the relationship between tests and the code being tested.



### Principles

- **Dependency Rule**: This rule states that source code dependencies can only point inwards. Nothing in an inner circle can know anything at all about something in an outer circle.

- **Independent of Frameworks**: The architecture does not depend on the existence of some library of feature-laden software. This allows you to use such frameworks as tools, rather than having to cram your system into their limited constraints.

- **Testable**: The business rules can be tested without the UI, Database, Web Server, or any other external element.

- **Independent of UI**: The UI can change easily, without changing the rest of the system. A Web UI could be replaced with a console UI, for example, without changing the business rules.

- **Independent of Database**: You can swap out SQL for NoSQL or vice versa without changing the business logic.

- **Independent of any External Agency**: In general, the business rules simply don’t know anything at all about the outside world.


## Structure of the Project 

```
src/
|-- core/                        # Entity layer (business rules/logic)
|   |-- domain/                  # Domain models/entities
|   |   |-- indicators/
|   |   |   |-- base_indicator.py
|   |   |   |-- F1_1.py
|   |   |   `-- ...
|   |   |-- analysis/
|	|   |-- pre-transformation/
|	|	|	|-- bioconductor/
|	|	|	|	`-- model.py
|	|	|	`-- bioconda/
|	|	|		`-- model.py
|   |   `-- repositories/         # Repository interfaces
|   |       `-- user_repository.py
|   |-- use_cases/               # Use case layer (application-specific business rules)
|   |   |-- data_importation/
|   |   |   |-- bioconductor/
|   |   |   |-- bioconda/
|   |   |   `-- ...
|   |   |-- data_transformation/
|   |   |   |-- transformer_interface.py  # Shared transformer interface
|   |   |   |-- bioconductor/
|   |   |   |-- bioconda/
|   |   |   `-- ...
|   |   |-- integration_task/
|   |   |-- indicators_evaluation/
|   |   |   |-- calculate_findability_for_custom_data.py # Use or extend domain's indicators
|   |   |   `-- ...
|   |   `-- analysis/
|   `-- shared/                  # Shared functionalities across use cases
|       |-- common_functions.py
|       `-- ...
|
|-- adapters/                    # Interface Adapter layer 
|   |-- repository/              # Data access mechanisms
|       |-- mongo_user_repository.py
|       |-- mongo_project_repository.py
|   |-- api/                     # API interfaces (REST, GraphQL, etc.)
|   `-- cli/                     # CLI interfaces
|
|-- infrastructure/              # Frameworks & Drivers layer
|   |-- db/
|       |-- mongo_client.py
|   `-- web_server/
|
`-- config/                      # Application configurations
|   |-- database_config.py
|   `-- ...
|
`-- cli/                         # Interact with the use cases 
    `-- data_processing_script.py
```
### An example of how the layers interact
#### Core 

```python
# core/domain/repositories/user_repository.py

from abc import ABC, abstractmethod
from typing import List
from core.domain.entities.user import User

class IUserRepository(ABC):
    @abstractmethod
    def add_user(self, user: User) -> None:
        pass

    @abstractmethod
    def get_user(self, user_id: str) -> User:
        pass

    @abstractmethod
    def list_users(self) -> List[User]:
        pass
```

#### Frameworks & Drivers


This setup centralizes your MongoDB configuration and connection logic, making it easier to manage and reuse across different parts of your application.

```python
# infrastructure/db/mongo_client.py

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

class MongoDBClient:
    def __init__(self, uri, dbname):
        self.uri = uri
        self.dbname = dbname
        self.client = None
        self.db = None

    def connect(self):
        """Connect to MongoDB and select the database."""
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[self.dbname]
            # Test connection
            self.client.admin.command('ping')
            print("MongoDB connection successful.")
        except ConnectionFailure:
            print("MongoDB connection failed.")
            self.client = None

    def get_database(self):
        """Return the database instance if connected."""
        if self.client and self.db:
            return self.db
        else:
            print("Not connected to MongoDB.")
            return None

    def close(self):
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()
            print("MongoDB connection closed.")
```

#### Interface Adapter

Different operations that interact with the database, such as queries, document updates, insertions, deletions, and any other database operations required by your application. 

The repository implements methods for CRUD operations using the PyMongo library's syntax for interacting with MongoDB. It would use the MongoDB client setup from the `infrastructure/db/mongo_client.py`:

```python

# adapters/repository/mongo_user_repository.py

from core.domain.repositories.user_repository import IUserRepository
from core.domain.entities.user import User
from infrastructure.db.mongodb_client import MongoDBClient
from bson import ObjectId

class MongoDBUserRepository(IUserRepository):
    def __init__(self, client: MongoDBClient):
        self.client = client
        self.client.connect()
        self.db = self.client.get_database()

    def add_user(self, user: User) -> None:
        user_data = user.to_dict()  # Assuming User entity has a to_dict method for serialization
        self.db.users.insert_one(user_data)

    def get_user(self, user_id: str) -> User:
        user_data = self.db.users.find_one({"_id": ObjectId(user_id)})
        if user_data:
            return User.from_dict(user_data)  # Assuming a from_dict method for deserialization
        return None

    def list_users(self) -> List[User]:
        users = self.db.users.find()
        return [User.from_dict(user_data) for user_data in users]
```

> ❗️ The core application interacts with the database through these repositories, not directly with MongoDB. This separation allows you to change the underlying database technology without impacting the core business logic, adhering to the principles of Clean Architecture.

### Use Case

```python

# src/core/use_cases/create_user.py

class CreateUserUseCase:
    def __init__(self, user_repository):
        self.user_repository = user_repository

    def execute(self, user_data):
        # Here, user_data would be a dict or object containing user details
        # Validate user_data as needed
        
        # Assuming User is a domain entity and from_dict is a method to instantiate it from user_data
        user = User.from_dict(user_data)
        
        # Add the user to the repository
        self.user_repository.add_user(user)
        
        # Return some result or confirmation
        return {"status": "success", "user_id": str(user.id)}
```

Finally, we can execute the use case by wiring together the different layer of the application:

```python

# Example instantiation and execution (simplified for clarity)

from infrastructure.mongodb.mongodb_client import MongoDBClient
from infrastructure.mongodb.mongodb_user_repository import MongoDBUserRepository
from core.use_cases.create_user import CreateUserUseCase

# Setup MongoDB client and repository
mongodb_client = MongoDBClient("mongodb://localhost:27017", "mydatabase")
user_repository = MongoDBUserRepository(mongodb_client)

# Instantiate the use case with its required repository
create_user_use_case = CreateUserUseCase(user_repository)

# Execute the use case with some user data
result = create_user_use_case.execute({"name": "John Doe", "email": "john@example.com"})

print(result)

```

> ❗️ This is a simplified example to illustrate the interaction between the different layers. 
> In a real-world application, this kind of code can be part of a controller:
>```
> src/
>|-- web/
>    |-- controllers/
>        |-- user_controller.py
>```
> a service layer that handles the request/response cycle in a web application:
>```
>src/
>|-- application/
>    |-- services/
>        |-- user_service.py
>```
> a Command Line Interface (CLI) Tool:
>```
>src/
>|-- application/
>    |-- services/
>        |-- user_service.py
>```
> or a script that processes data:
>```
>src/
>|-- core/
>|-- use_cases/
>|-- infrastructure/
>|-- cli/
>    |-- data_processing_script.py
>```