from sqlalchemy import Column, Integer, BigInteger, String, Float, Date, DateTime, Text, ForeignKey
from sqlalchemy.sql import func

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    profile_image = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class UserMLMapping(Base):
    __tablename__ = "user_ml_mapping"

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        primary_key=True
    )

    ml_user_id = Column(
        Integer,
        unique=True,
        nullable=False
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )


class Movie(Base):
    __tablename__ = "movies"

    movie_id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    genres = Column(String(500), nullable=True)
    release_year = Column(Integer, nullable=True)
    tmdb_id = Column(Integer, nullable=True)
    poster_url = Column(String(1000), nullable=True)
    backdrop_url = Column(String(1000), nullable=True)
    overview = Column(Text, nullable=True)
    runtime = Column(Integer, nullable=True)
    tmdb_rating = Column(Float, nullable=True)   # TMDB vote_average (0–10)


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(BigInteger, primary_key=True, index=True)
    ml_user_id = Column(Integer, nullable=False)
    movie_id = Column(Integer, nullable=False)
    rating = Column(Float, nullable=False)
    rated_at = Column(Date, nullable=True)


class UserRating(Base):
    __tablename__ = "user_ratings"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    movie_id = Column(Integer, nullable=False)
    rating = Column(Float, nullable=False)
    rated_at = Column(DateTime, server_default=func.now())


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    movie_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class WatchHistory(Base):
    __tablename__ = "watch_history"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    movie_id = Column(Integer, nullable=False)
    watched_at = Column(DateTime, server_default=func.now())