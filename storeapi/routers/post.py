import logging
import sqlalchemy
from enum import Enum
from typing import Annotated
from pydantic.types import List
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status, Depends
from storeapi.models.post import Comment, CommentIn, UserPost, UserPostIn, PostLike, PostLikeIn, UserPostWithLikes
from storeapi.models.user import User
from storeapi.database import like_table, post_table, comment_table, database
from storeapi.security import get_current_user
from storeapi.tasks import generate_and_add_to_post

router = APIRouter()
logger = logging.getLogger(__name__)

select_post_likes = (
    sqlalchemy.select(post_table, sqlalchemy.func.count(like_table.c.id).label("likes"))
    .select_from(post_table.outerjoin(like_table))
    .group_by(post_table.c.id)
)

class PostSorting(str, Enum):
    new = "new"
    old = "old"
    most_likes = "most_likes"

async def find_post(post_id: int):
    logger.info(f"Finding post with id {post_id}")
    query = post_table.select().where(post_table.c.id == post_id)
    logger.debug(query, extra={"email": "wesley@fullstacklabs.co"})
    return await database.fetch_one(query)

@router.get("/post", response_model=List[UserPostWithLikes])
async def get_posts(sorting: PostSorting = PostSorting.new):
    logger.info("Getting all the posts")

    match sorting:
        case PostSorting.new:
            query = select_post_likes.order_by(post_table.c.id.desc())

        case PostSorting.old:
            query = select_post_likes.order_by(post_table.c.id.asc())

        case PostSorting.most_likes:
            query = select_post_likes.order_by(sqlalchemy.desc("likes"))        
    
    logger.debug(query)
    return await database.fetch_all(query)

@router.post("/post", response_model=UserPost, status_code=status.HTTP_201_CREATED)
async def create_post(post: UserPostIn, current_user: Annotated[User, Depends(get_current_user)], background_tasks: BackgroundTasks, request: Request, prompt: str = None):
    logger.info("Creating a new post")
    data = {**post.model_dump(), "user_id": current_user.id}
    query = post_table.insert().values(data)
    logger.debug(query)
    last_record_id = await database.execute(query)
    if prompt:
        background_tasks.add_task(generate_and_add_to_post, current_user.email, last_record_id, request.url_for("get_post_comments", post_id=last_record_id), database, prompt)
    return {**data, "id": last_record_id}

@router.get("/post/{post_id}", response_model=UserPostWithLikes)
async def get_post_comments(post_id: int):
    logger.info(f"Getting the comments of a post with id {post_id}")
    query = select_post_likes.where(post_table.c.id == post_id)
    logger.debug(query)
    post = await database.fetch_one(query)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    
    return {
        "post": post,
        "comments": await get_post_comment(post_id)
    }

@router.get("/post/{post_id}/comment", response_model=List[Comment])
async def get_post_comment(post_id: int):
    query = comment_table.select().where(comment_table.c.post_id == post_id)
    logger.debug(query)
    return await database.fetch_all(query)

@router.post("/comment", response_model=Comment, status_code=status.HTTP_201_CREATED)
async def create_comment(comment: CommentIn, current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Creating a new comment")
    post = await find_post(comment.post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    
    data = {**comment.model_dump(), "user_id": current_user.id}
    query = comment_table.insert().values(data)
    logger.debug(query)
    last_record_id = await database.execute(query)
    return {**data, "id": last_record_id}

@router.post("/like", response_model=PostLike, status_code=status.HTTP_201_CREATED)
async def like_post(like: PostLikeIn, current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Liking post")
    post = await find_post(like.post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    
    data = {**like.model_dump(), "user_id": current_user.id}
    query = like_table.insert().values(data)
    logger.debug(query)
    last_record_id = await database.execute(query)
    return {**data, "id": last_record_id}
