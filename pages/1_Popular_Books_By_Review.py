# Import python packages
import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd
from datetime import datetime

def get_reviews_daterange(_session):
    query = """
        select min(date), max(date) from reviews;
    """
    data = _session.sql(query).collect()
    return data[0][0], data[0][1]
    
def get_books(_session):
    query = """
    select * from LIBRARYSYSTEM.PUBLIC.BOOKS
    """
    data = _session.sql(query).collect()
    return pd.DataFrame(data)

def get_books_with_reviews(_session, from_date, to_date, query_limit, by='count', min_reviews=100):
    order = 'average_rating' if by == 'avg' else 'review_count'
    reviews = f'where review_count >= {min_reviews}' if by == 'avg' else ''
    query = f"""
    select books.bib_number, books.title, books.publication_year, agg.review_count, agg.average_rating from
        (select b.bib_number, count( * ) as review_count, avg(r.rating) as average_rating from books b
            join reviews r
            on b.bib_number = r.bib_number
            where r.date >= '{from_date}'
              and r.date <= '{to_date}'
            group by b.bib_number) as agg
        left join books
        on books.bib_number = agg.bib_number
        {reviews}
        order by {order} desc
        limit {query_limit}
    """
    data = _session.sql(query).collect()
    return pd.DataFrame(data)

def format_with_commas(number):
    return f"{number:,}"



# Write directly to the app
st.title("Popular Books By Review")

# Get the current credentials
session = get_active_session()

first_review_date, last_review_date = get_reviews_daterange(session)

col = st.columns(3)
with col[0]:
    start_date = st.date_input("Start date", first_review_date,
            min_value=first_review_date, max_value=last_review_date)
with col[1]:
    end_date = st.date_input("End date", last_review_date,
                min_value=start_date, max_value=last_review_date)
with col[2]:
    query_limit = st.number_input('Query Limit', value=100,
                min_value=1, max_value=1000)

# date_from = int(start_date[0:4]), int(start_date[5:7]), int(start_date[8:10])
# st.write(date_from)

st.subheader('Most Popular Books in Date Range (By Number of Reviews)')
books_reviews_df = get_books_with_reviews(session, start_date, end_date, query_limit)
st.dataframe(books_reviews_df, column_config={"BIB_NUMBER": st.column_config.NumberColumn(format="%d")})

st.subheader('Highest Reviewed Books in Date Range (By Average Rating)')
min_reviews = st.number_input('Minimum Number of Reviews', value=100,
                min_value=1, max_value=10000)
books_reviews_avg_df = get_books_with_reviews(session, start_date, end_date, query_limit, by='avg', min_reviews=min_reviews)
st.dataframe(books_reviews_avg_df, column_config={"BIB_NUMBER": st.column_config.NumberColumn(format="%d")})