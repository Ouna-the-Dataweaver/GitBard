from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class ProjectInfo(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    web_url: str
    path_with_namespace: str


class ObjectAttributes(BaseModel):
    id: int
    iid: Optional[int] = None
    action: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    state: Optional[str] = None
    note: Optional[str] = None
    noteable_type: Optional[str] = None
    url: Optional[str] = None


class MergeRequest(BaseModel):
    id: int
    iid: int
    title: str
    description: Optional[str] = None
    source_branch: str
    target_branch: str
    state: str
    author_id: int


class User(BaseModel):
    id: int
    name: str
    username: str
    email: str


class GitLabWebhook(BaseModel):
    object_kind: str = Field(..., description="Type of webhook event")
    event_type: Optional[str] = None
    user: Optional[User] = None
    project: Optional[ProjectInfo] = None
    object_attributes: Optional[ObjectAttributes] = None
    merge_request: Optional[MergeRequest] = None


class WebhookResponse(BaseModel):
    status: str
    event_type: Optional[str] = None
    project: Optional[str] = None
    message: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    gitlab_url: str
