# Import python packages
import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd

def get_checkouts_daterange(_session):
    query = """
        select min(month), max(month) from checkouts;
    """
    data = _session.sql(query).collect()
    min_month = data[0][0].split('-')
    max_month = data[0][1].split('-')

    return (int(min_month[0]), int(min_month[1])), (int(max_month[0]), int(max_month[1]))

def get_books_with_checkouts(_session, from_date, to_date, query_limit):
    query = f"""
    select popular_books.bib_number, books.title, books.publication_year, popular_books.total_checkouts
        from (select bib_number, sum(checkouts) as total_checkouts from checkouts
        where month >= '{from_date}'
          and month <= '{to_date}'
        group by bib_number
        order by total_checkouts desc
        limit {query_limit}) as popular_books
        join books
        on popular_books.bib_number = books.bib_number
        order by total_checkouts desc
    """
    data = _session.sql(query).collect()
    return pd.DataFrame(data)

def get_authors_with_checkouts(_session, from_date, to_date, query_limit):
    query = f"""
    select authors.author_id, authors.name, total_checkouts
        from (select author_id, sum(checkouts) as total_checkouts from checkouts
        join authored_book as ab on checkouts.bib_number = ab.bib_number
        where month >= '{from_date}'
        and month <= '{to_date}'
        group by author_id
        order by total_checkouts desc
        limit {query_limit}) as popular_authors
        join authors on popular_authors.author_id = authors.author_id
        order by total_checkouts desc
        """
    data = _session.sql(query).collect()
    return pd.DataFrame(data)


def pad(text, pad_with = '0', pad_to = 2):
    return f"{pad_with * pad_to}{text}"[-1 * pad_to:]

# Write directly to the app
st.title("Popular Books By Checkouts")

# Get the current credentials
session = get_active_session()

first_checkout_month, last_checkout_month = get_checkouts_daterange(session)

from_year, from_month = first_checkout_month
to_year, to_month = last_checkout_month
year_range = range(first_checkout_month[0], last_checkout_month[0] + 1)

col = st.columns(5)
with col[0]:
    from_year = st.selectbox("From year", year_range)
with col[1]:
    first_month = first_checkout_month[1] if from_year == first_checkout_month[0] else 1
    last_month = last_checkout_month[1] if from_year == last_checkout_month[0] else 12
    from_month = st.selectbox("From month", range(first_month, last_month + 1))
with col[2]:
    to_year = st.selectbox("To year", year_range, index=len(year_range)-1)
with col[3]:
    first_month = first_checkout_month[1] if to_year == first_checkout_month[0] else 1
    last_month = last_checkout_month[1] if to_year == last_checkout_month[0] else 12
    to_month_range = range(first_month, last_month + 1)
    to_month = st.selectbox("To month", to_month_range, index=len(to_month_range) - 1)
with col[4]:
    query_limit = st.number_input('Query Limit', value=100,
                min_value=1, max_value=1000)


from_date = f"{from_year}-{pad(from_month)}"
to_date = f"{to_year}-{pad(to_month)}"
if(from_date > to_date):
    st.warning('From date cannot be greater than to date')
    st.stop()

# date_from = int(start_date[0:4]), int(start_date[5:7]), int(start_date[8:10])
# st.write(date_from)

st.subheader('Most Popular Books in Date Range (By Number of Checkouts)')
books_checkouts_df = get_books_with_checkouts(session, from_date, to_date, query_limit)
st.dataframe(books_checkouts_df, column_config={"BIB_NUMBER": st.column_config.NumberColumn(format="%d")})

st.subheader('Most Popular Authors in Date Range (By Number of Checkouts)')
authors_checkouts_df = get_authors_with_checkouts(session, from_date, to_date, query_limit)
st.dataframe(authors_checkouts_df, column_config={"AUTHOR_ID": st.column_config.NumberColumn(format="%d")})
