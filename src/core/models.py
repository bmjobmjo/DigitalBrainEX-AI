"""
SQLAlchemy 2.0 ORM Models for DigitalBrainEX AI.
100% faithful representation of all 15 SQLite tables in DevDiary.db3.
"""
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    LargeBinary,
    Numeric,
    DateTime,
    Boolean,
)
from src.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    PojectID = Column(Integer, primary_key=True, autoincrement=True)
    ProjectName = Column(Text, nullable=True)
    Desc = Column(Text, nullable=True)
    Notes = Column(Text, nullable=True)
    CreationDateInt = Column(Integer, nullable=True)
    CreationDate = Column(Integer, nullable=True)
    StartDate = Column(Text, nullable=True)
    StartDateInt = Column(Integer, nullable=True)
    Status = Column(Text, nullable=True, default="Active")
    ProjGUID = Column(Text, nullable=True)
    UploadedTime = Column(Text, nullable=True)
    UploadRetry = Column(Integer, default=0)
    DirtyFlag = Column(Integer, default=1)

    # Convenient alias properties
    @property
    def id(self):
        return self.PojectID

    @property
    def name(self):
        return self.ProjectName or ""


class DocumentCategory(Base):
    __tablename__ = "documentsCatogory"

    CatgoryID = Column(Integer, primary_key=True, autoincrement=True)
    CatogoryName = Column(Text, nullable=True)

    @property
    def id(self):
        return self.CatgoryID

    @property
    def name(self):
        return self.CatogoryName or ""


class Document(Base):
    """
    Document item. The 'Type' column distinguishes:
      0 = Document / File
      1 = Code Snippet
      2 = Meeting Minutes
      3 = Note
    """
    __tablename__ = "documents"

    DocumentID = Column(Integer, primary_key=True, autoincrement=True)
    PojectID = Column(Integer, nullable=True)
    ProjectName = Column(Text, nullable=True)
    DocumentName = Column(Text, nullable=True)
    DocumentURI = Column(Text, nullable=True)
    Desc = Column(Text, nullable=True)
    Notes = Column(Text, nullable=True)
    Version = Column(Text, nullable=True)
    Category = Column(Text, nullable=True)
    AddedOn = Column(Text, nullable=True)
    AddedOnInt = Column(Integer, nullable=True)
    ModifiedDate = Column(Integer, nullable=True)
    Type = Column(Integer, default=0)
    Language = Column(Text, nullable=True)
    DocGUID = Column(Text, nullable=True)
    DirtyFlag = Column(Integer, default=1)
    uploadedTime = Column(Text, nullable=True)
    UploadRetry = Column(Integer, default=0)
    AddToLLM = Column(Integer, default=0)
    AudioStatus = Column(Integer, default=0)

    @property
    def id(self):
        return self.DocumentID

    @property
    def name(self):
        return self.DocumentName or ""


class Url(Base):
    __tablename__ = "urls"

    UrlID = Column(Integer, primary_key=True, autoincrement=True)
    PojectID = Column(Numeric, nullable=True)
    ProjectName = Column(Text, nullable=True)
    Url = Column(Text, nullable=True)
    UrlName = Column(Text, nullable=True)
    Notes = Column(Text, nullable=True)
    Category = Column(Text, nullable=True)
    AddedOn = Column(Text, nullable=True)
    AddedOnInt = Column(Integer, nullable=True)
    UrlGUID = Column(Text, nullable=True)
    DirtyFlag = Column(Integer, default=1)
    UploadedTime = Column(Text, nullable=True)

    @property
    def id(self):
        return self.UrlID


class Task(Base):
    __tablename__ = "tasks"

    TaskID = Column(Integer, primary_key=True, autoincrement=True)
    TaskName = Column(Text, nullable=True)
    TaskDesc = Column(Text, nullable=True)
    Type = Column(Text, default="T")
    DueOn = Column(Text, nullable=True)
    ProjectID = Column(Text, nullable=True)
    ProjectName = Column(Text, nullable=True)
    Status = Column(Text, default="Active")
    RemType = Column(Text, default="No")
    ReminderTimeHHMM = Column(Text, default="00:00")
    ReminderWMDay = Column(Text, nullable=True)
    RepeatInterval = Column(Integer, nullable=True)
    RepeatMonth = Column(Text, nullable=True)
    AlertedOn = Column(Text, default="2000-01-01")
    ToDaysTask = Column(Text, default="2000-01-01")
    UserClosed = Column(Text, default="NO")
    EarlyRem = Column(Text, default="NO")
    Snooze = Column(Integer, default=0)
    SnoozedON = Column(Text, default="2000-01-01")
    Priority = Column(Integer, default=0)
    TriggeredTimeStamp = Column(Integer, nullable=True)
    TodayOrder = Column(Integer, nullable=True)
    TodayDue = Column(Text, nullable=True)
    TaskGUID = Column(Text, nullable=True)
    DirtyFlag = Column(Integer, default=1)
    UploadedTime = Column(Text, nullable=True)
    UploadRetry = Column(Integer, default=0)

    @property
    def id(self):
        return self.TaskID


class Secret(Base):
    __tablename__ = "secrets"

    SecretID = Column(Integer, primary_key=True, autoincrement=True)
    SecretName = Column(Text, nullable=True)
    ApplicationURL = Column(Text, nullable=True)
    Identity = Column(Text, nullable=True)
    Password = Column(Text, nullable=True)
    Desc = Column(Text, nullable=True)
    Status = Column(Text, default="Active")
    UpdatedON = Column(Text, nullable=True)
    ProjectID = Column(Text, nullable=True)
    ProjectName = Column(Text, nullable=True)
    FPPass = Column(Text, nullable=True)
    FPIden = Column(Text, nullable=True)
    FPKey = Column(Text, nullable=True)
    SecGUID = Column(Text, nullable=True)
    DirtyFlag = Column(Integer, default=1)
    UploadedTime = Column(Text, nullable=True)
    UploadRetry = Column(Integer, default=0)

    @property
    def id(self):
        return self.SecretID


class TrackMe(Base):
    __tablename__ = "trackme"

    TrackID = Column(Integer, primary_key=True, autoincrement=True)
    ProjectID = Column(Integer, nullable=True)
    ProjectName = Column(Text, nullable=True)
    Application = Column(Text, nullable=True)
    WindowTitle = Column(Text, nullable=True)
    Seconds = Column(Integer, nullable=True)
    DateTime = Column(Text, nullable=True)

    @property
    def id(self):
        return self.TrackID


class Goal(Base):
    __tablename__ = "Goals"

    GoalID = Column(Integer, primary_key=True, autoincrement=True)
    Goal = Column(Text, nullable=True)
    Desc = Column(Text, nullable=True)
    ProjectName = Column(Text, nullable=True)
    ProjectID = Column(Integer, nullable=True)
    StartDate = Column(Text, nullable=True)
    FinishDate = Column(Text, nullable=True)
    ExtendedDate = Column(Text, nullable=True)
    AchivedDate = Column(Text, nullable=True)
    AssignedTo = Column(Text, nullable=True)
    ScheduleFileURI = Column(Text, nullable=True)

    @property
    def id(self):
        return self.GoalID


class WatchFolder(Base):
    __tablename__ = "WatchFolder"

    FolderPath = Column(Text, primary_key=True)


class Embedding(Base):
    __tablename__ = "Embeddings"

    # SQLite table has no explicit PK defined; we designate FileFullPath + TextPointer as composite key
    FileFullPath = Column(Text, primary_key=True)
    TextPointer = Column(Text, primary_key=True)
    FileName = Column(Text, nullable=True)
    ProjectName = Column(Text, nullable=True)
    TextFilePath = Column(Text, nullable=True)
    Embedding = Column(LargeBinary, nullable=True)
    Date = Column(Text, nullable=True)
    ProjectID = Column(Text, nullable=True)
    DocumentID = Column(Integer, nullable=True)


class EmbeddingBackup(Base):
    __tablename__ = "Embeddings_backup"

    FileFullPath = Column(Text, primary_key=True)
    TextPointer = Column(Text, primary_key=True)
    FileName = Column(Text, nullable=True)
    ProjectName = Column(Text, nullable=True)
    TextFilePath = Column(Text, nullable=True)
    Embedding = Column(LargeBinary, nullable=True)
    Date = Column(Text, nullable=True)
    ProjectID = Column(Text, nullable=True)


class TrackTempFileToDocConv(Base):
    __tablename__ = "TrackTempFileToDocConv"

    DocumentID = Column(Integer, primary_key=True)
    RetryCount = Column(Integer, default=0)
    FailReason = Column(Text, nullable=True)


class ClipboardHistory(Base):
    __tablename__ = "ClipboardHistory"

    ID = Column(Integer, primary_key=True, autoincrement=True)
    ContentType = Column(Text, nullable=True)  # "Text" or "Image"
    TextContent = Column(Text, nullable=True)
    ImagePath = Column(Text, nullable=True)
    AddedOn = Column(Text, nullable=True)

    @property
    def id(self):
        return self.ID


class SchemaVer(Base):
    __tablename__ = "schemaVer"

    SchemaID = Column(Integer, primary_key=True)
    Version = Column(Integer, nullable=True)
