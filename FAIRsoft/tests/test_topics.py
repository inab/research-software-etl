from FAIRsoft.classes.topic_operation import vocabularyItem, vocabulary_topic, HttpUrl
import pytest

class TestVocabularyItems:

    # Creating a vocabulary_topic object with a valid EDAM URI and topic path should be successful
    def test_valid_EDAM_URI_and_topic_path(self):
        uri = "http://edamontology.org/topic_0084"
        term = "Phylogeny"
        obj = vocabularyItem(uri=uri, term=term)
        assert obj.uri == HttpUrl(uri)
        assert obj.term == term
        assert obj.vocabulary == "EDAM"

    # Creating a vocabulary_topic object with a valid non-EDAM URI should be successful
    def test_valid_non_EDAM_URI(self):
        uri = "https://example.com"
        term = "Phylogeny"
        obj = vocabularyItem(uri=uri, term=term)
        assert obj.uri == HttpUrl(uri)
        assert obj.term == term
        assert obj.vocabulary == ""

    # Creating a vocabulary_topic object with a valid non-topic EDAM URI should be successful
    def test_valid_non_topic_EDAM_URI(self):
        uri = "http://edamontology.org/data_0084"
        term = "Phylogeny"
        obj = vocabularyItem(uri=uri, term=term)
        assert obj.uri == HttpUrl(uri)
        assert obj.term == term
        assert obj.vocabulary == "EDAM"

    # Creating a vocabulary_topic object with an empty URI and non-empty term should populate the URI field with the EDAM URI
    def test_empty_URI_non_empty_term(self):
        uri = ""
        term = "Phylogeny"

        obj = vocabularyItem(term=term, uri=None)

        assert obj.uri == HttpUrl('http://edamontology.org/topic_0084')
        assert obj.term == "Phylogeny"
        assert obj.vocabulary == "EDAM"
        

    # Creating a vocabulary_topic object with an empty URI and empty term should raise a ValueError
    def test_empty_URI_empty_term(self):
        uri = ""
        term = ""
        with pytest.raises(ValueError):
            obj = vocabularyItem(uri=uri, term=term)

    # Creating a vocabulary_topic object with a non-HTTP/HTTPS URI and non-empty term should raise a ValueError
    def test_non_HTTPS_URI_non_empty_term(self):
        uri = "ftp://edam.org/topic_0084"
        term = "Phylogeny"
        with pytest.raises(ValueError):
            obj = vocabularyItem(uri=uri, term=term)

class TestVocabularyTopic:

    # Creating a vocabulary_topic object with a valid EDAM URI and topic should succeed.
    def test_valid_EDAM_URI_and_topic(self):
        # Arrange
        uri = "http://edamontology.org/topic_0084"
        topic = "Phylogeny"
    
        # Act
        obj = vocabulary_topic(uri=uri, term=topic)
    
        # Assert
        assert obj.uri == HttpUrl(uri)
        assert obj.term == topic
        assert obj.vocabulary == "EDAM"

    # Creating a vocabulary_topic object with a valid EDAM URI and non-topic should not succeed.
    def test_valid_EDAM_URI_and_non_topic(self):
        # Arrange
        uri = "http://edamontology.org/format_0001"
        term = "FASTA"
    
        # Act and Assert
        with pytest.raises(ValueError):
            obj = vocabulary_topic(uri=uri, term=term)
    
        

    # Creating a vocabulary_topic object with a valid non-EDAM URI and topic should succeed.
    def test_valid_non_EDAM_URI_and_topic(self):
        # Arrange
        uri = "http://example.com/topic_0001"
        topic = "Custom Topic"
        vocabulary = "Custom Vocabulary"
    
        # Act
        obj = vocabulary_topic(uri=uri, term=topic, vocabulary=vocabulary)
    
        # Assert
        assert obj.uri == HttpUrl(uri)
        assert obj.term == topic
        assert obj.vocabulary == "Custom Vocabulary"

    # Creating a vocabulary_topic object with an empty URI and empty topic should fail.
    def test_empty_URI_and_topic(self):
        # Arrange
        uri = ""
        topic = ""
    
        # Act and Assert
        with pytest.raises(ValueError):
            obj = vocabulary_topic(uri=uri, term=topic)

    # Creating a vocabulary_topic object with an empty URI and valid topic should fail.
    def test_empty_URI_and_valid_topic(self):
        # Arrange
        uri = ""
        topic = "Bioinformatics"
    
        # Act and Assert
        obj = vocabulary_topic(term=topic, uri=uri)

        assert obj.uri == HttpUrl('http://edamontology.org/topic_0091')
        assert obj.term == topic
        assert obj.vocabulary == "EDAM"



    # Creating a vocabulary_topic object with a valid URI and empty topic should not populate the remaining fields.
    def test_valid_URI_and_empty_topic(self):
        # Arrange
        uri = "http://edamontology.org/topic_0084"
        topic = ""
    
        # Act
        obj = vocabulary_topic(uri=uri, term=topic)

        print(obj.uri.host)

        assert obj.uri == HttpUrl(uri)
        assert obj.term == "Phylogeny"
        assert obj.vocabulary == "EDAM"