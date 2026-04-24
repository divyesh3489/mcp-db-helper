from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime, timedelta, timezone
import random
import os

# Database setup
DATABASE_URL = "sqlite:///movie_blog.db"

# Remove existing database to avoid constraint conflicts
if os.path.exists("movie_blog.db"):
    os.remove("movie_blog.db")
    print("✓ Removed existing database")

engine = create_engine(DATABASE_URL)
Base = declarative_base()

# Define Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    
    blogs = relationship("Blog", back_populates="author")
    ratings = relationship("Rating", back_populates="user")

class Blog(Base):
    __tablename__ = "blogs"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    movie_title = Column(String(100), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    author = relationship("User", back_populates="blogs")
    ratings = relationship("Rating", back_populates="blog")

class Rating(Base):
    __tablename__ = "ratings"
    
    id = Column(Integer, primary_key=True)
    blog_id = Column(Integer, ForeignKey("blogs.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Float, nullable=False)  # 1-5 scale
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    blog = relationship("Blog", back_populates="ratings")
    user = relationship("User", back_populates="ratings")

# Create tables
Base.metadata.create_all(engine)

# Create session
Session = sessionmaker(bind=engine)
session = Session()

# Dummy data
usernames = ["alice_film", "bob_cinema", "charlie_movies", "diana_critic", "eve_reviewer", "frank_buff", "grace_fan"]
emails = ["alice@movie.com", "bob@cinema.com", "charlie@flicks.com", "diana@critic.com", "eve@review.com", "frank@film.com", "grace@fan.com"]

movies = [
    "The Shawshank Redemption",
    "The Dark Knight",
    "Inception",
    "Pulp Fiction",
    "Forrest Gump",
    "The Matrix",
    "Gladiator",
    "Interstellar",
    "The Avengers",
    "Parasite"
]

blog_templates = [
    "This movie is absolutely stunning! {movie} truly captured my heart with its incredible storytelling and stellar cast.",
    "A masterpiece! {movie} is a journey that will stay with you long after the credits roll.",
    "{movie} exceeded all my expectations. The cinematography and acting were top-notch.",
    "One of the best films I've ever seen. {movie} is a testament to modern filmmaking excellence.",
    "Highly recommend {movie}! It's a gem that shouldn't be missed by any movie enthusiast.",
    "{movie} is a thrilling experience from start to finish. Absolutely loved every minute!",
    "A remarkable film. {movie} demonstrates the power of great storytelling and brilliant direction.",
]

comments = [
    "Great review! I completely agree.",
    "This movie deserves all the praise.",
    "Not sure I agree, but nice perspective.",
    "Perfectly written review!",
    "You captured the essence of the film beautifully.",
    "Couldn't have said it better myself.",
    "Interesting take on the movie.",
    "This convinced me to watch it!",
]

# Create users
print("Creating users...")
users = []
for username, email in zip(usernames, emails):
    user = User(username=username, email=email)
    session.add(user)
    users.append(user)

session.commit()
print(f"✓ Created {len(users)} users")

# Create blogs
print("Creating blogs...")
blogs = []
for i in range(15):
    movie = random.choice(movies)
    author = random.choice(users)
    blog = Blog(
        title=f"Review: {movie}",
        content=random.choice(blog_templates).format(movie=movie),
        movie_title=movie,
        author_id=author.id,
        created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))
    )
    session.add(blog)
    blogs.append(blog)

session.commit()
print(f"✓ Created {len(blogs)} blogs")

# Create ratings
print("Creating ratings...")
ratings_count = 0
for blog in blogs:
    # Each blog gets 2-5 ratings
    num_ratings = random.randint(2, 5)
    possible_raters = [u for u in users if u.id != blog.author_id]
    raters = random.sample(possible_raters, min(num_ratings, len(possible_raters)))
    
    for rater in raters:
        rating = Rating(
            blog_id=blog.id,
            user_id=rater.id,
            rating=round(random.uniform(3.0, 5.0), 1),
            comment=random.choice(comments),
            created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 28))
        )
        session.add(rating)
        ratings_count += 1

session.commit()
print(f"✓ Created {ratings_count} ratings")

print("\n" + "="*50)
print("✓ Dummy data successfully created!")
print("="*50)
print(f"Database: movie_blog.db")
print(f"Users: {len(users)}")
print(f"Blogs: {len(blogs)}")
print(f"Ratings: {ratings_count}")
print("="*50)

session.close()
