from pydantic import BaseModel, EmailStr, field_validator, HttpUrl, model_validator
from enum import Enum
from typing import Optional
import re



class type_contributor(str, Enum):
    Person = 'Person'
    Organization = 'Organization'

    
class contributor(BaseModel):
    type: type_contributor = None
    name: str = None
    email: Optional[EmailStr] = None
    maintainer: bool = False
    url: Optional[HttpUrl] = None
    orcid: Optional[str] = None

    class Config:
        # Automatically serialize Enums to their string values
        json_encoders = {
            type_contributor: lambda v: v.value
        }

    @field_validator('name', mode="after")
    @classmethod
    def name_cannot_be_empty(cls, data):
        '''
        Name cannot be empty.
        '''
        if not data:
            raise ValueError("Name cannot be empty")
        else:
            return data
        
    @field_validator('type', mode="before")
    @classmethod
    def reclassify_organizations(cls, data):
        '''
        If type is Institute, Project, Funding Agency, etc..., reclassify to Organization
        '''
        org_keywords = ['institute', 'project', 'funding agency', 'division', 'consortium']
        for keyword in org_keywords:
            if data.lower() == keyword:
                return type_contributor.Organization
        
        return data
        

    @staticmethod
    def is_trash(data):
        '''
        Check if the data is trash.
        '''
        known_words = ['contributors', 'form', 'contact']
        for word in known_words:
            if word in data:
                return True
        
        return False
    
    
    @staticmethod
    def clean_brakets(string):
        '''
        Remove anything between {}, [], or <>, or after {, [, <
        '''
        def clena_after_braket(string):
            '''
            Remove anything between {}, [], or <>
            '''
            pattern = re.compile(r'\{.*|\[.*|\(.*|\<.*')
            return re.sub(pattern, '', string)

        def clean_between_brakets(string):
            '''
            Remove anything between {, [, <
            '''
            pattern = re.compile(r'\{.*?\}|\[.*?\]|\(.*?\)|\<.*?\>')
            return re.sub(pattern, '', string)

        def clean_before_braket(string):
            '''
            Remove anything before }, ], or >
            '''
            pattern = re.compile(r'.*?\}.*?|.*?\].*?|.*?\>.*?')
            return re.sub(pattern, '', string)


        string = clean_between_brakets(string)
        string = clena_after_braket(string)
        string = clean_before_braket(string)

        return string

    @staticmethod
    def clean_doctor(string):
        '''
        remove title at the begining of the string
        '''
        pattern = re.compile(r'^Dr\.|Dr |Dr\. |Dr')
        return re.sub(pattern, '', string)

    @staticmethod
    def keep_after_code(string):
        '''
        Remove anything before code and others
        '''
        if 'initial R code' in string:
            return ''
        if 'contact form' in string:
            return ''
        else:
            pattern = re.compile(r'.*?code')
            string = re.sub(pattern, '', string)
            pattern = re.compile(r'.*?Code')
            string = re.sub(pattern, '', string)
            pattern = re.compile(r'.*?from')
            string = re.sub(pattern, '', string)
            return re.sub(pattern, '', string)

    def clean_first_end_parenthesis(string):
        if string[0] == '(' and string[-1] == ')':
            string = string[1:]
            string = string[:-1]

        return string

    @staticmethod
    def clean_spaces(string):
        '''
        Clean spaces around the string
        '''
        return string.strip()

    @model_validator(mode="before")
    @classmethod
    def clean(cls, data):
        
        if isinstance(data, str):

            data = contributor.clean_first_end_parenthesis(data)
            data = contributor.clean_brakets(data)
            data = contributor.clean_doctor(data)
            data = contributor.keep_after_code(data)
            data = contributor.clean_spaces(data)

            if contributor.is_trash(data):
                return None
        
        return data
    
    
    @model_validator(mode="before")
    @classmethod
    def classify_person_organization(cls, data):
        if data.get('orcid'):
            data['type'] = type_contributor.Person

        return data

    @staticmethod
    def is_organization(data):
        '''
        NOt USED
        Check if the contributor is an organization.
        '''
        inst_keywords = [
            'university',
            'université',
            'universidad',
            'universidade',
            'università',
            'universität',
            'institut',
            'institute',
            'college',
            'school',
            'department',
            'laboratory',
            'laboratoire',
            'lab',
            'center',
            'centre',
            'research',
            'researcher',
            'researchers',
            'group',
            'support',
            'foundation',
            'company',
            'corporation',
            'team',
            'helpdesk',
            'service',
            'platform',
            'program',
            'programme',
            'community',
            'elixir'
        ]
        words = data.split()
        for word in words:
            if word.lower() in inst_keywords:
                return True

        return False

    def merge(self, other: 'contributor') -> 'contributor':
        if not isinstance(other, contributor):
            raise ValueError("Cannot merge with a non-contributor object")

        # Merge name: Prefer non-empty name
        self.name = self.name or other.name

        # Merge type: Prefer the type from 'self' if defined, otherwise take from 'other'
        self.type = self.type or other.type

        # Merge email: Prefer the non-null email
        self.email = self.email or other.email

        # Merge maintainer: If either is a maintainer, the merged result should be True
        self.maintainer = self.maintainer or other.maintainer

        # Merge URL: Prefer the non-null URL
        self.url = self.url or other.url

        # Merge ORCID: Prefer the non-null ORCID
        self.orcid = self.orcid or other.orcid

        return self
            
            