import numpy as np
import pandas as pd
import streamlit as st


def pad(text, pad_with = '0', pad_to = 2):
    return f"{pad_with * pad_to}{text}"[-1 * pad_to:]

def to_list(series):
    return ",".join(list(series.astype(str)))

def get_colors(n):
    COLORS = ['#556B2F', '#B8860B', '#3CB371', '#6495ED', '#F5F5DC', '#00FF7F', '#9400D3']
    repeats = (n // len(COLORS)) + ((n % len(COLORS)) > 0)
    return (COLORS * repeats)[0:n]

def divide_month(month):
    return tuple(map(int, month.split('-')))

def join_month(year, month):
    return f"{year}-{pad(month)}"

def get_daterange(from_date='2010-05', to_date='2020-01'):
    from_year, from_month = divide_month(from_date)
    to_year, to_month = divide_month(to_date)
    daterange = list()
    for year in range(from_year, to_year+1):
        for month in range(1, 13):
            daterange.append(join_month(year, month))
    return daterange[from_month-1:-1 * (12-to_month)]

@st.cache_data
def search_authors_with_checkouts(_connection, author_name, query_limit=10):
    query = f"""
    select searched_authors.author_id, searched_authors.name, total_checkouts
    from (
        select author_id, name from authors
            where lower(authors.name) like lower('%{author_name}%')
               or author_id like '%{author_name}%'
    ) as searched_authors
    join (select author_id, sum(checkouts) as total_checkouts from checkouts
        join authored_book as ab on checkouts.bib_number = ab.bib_number
        group by author_id
        order by total_checkouts desc) as popular_authors
        on popular_authors.author_id = searched_authors.author_id
        order by total_checkouts desc
        limit {query_limit}
        """
    data = _connection.query(query)
    return data

def get_authors_active_years(_connection, authors_list):
    query = f"""
    select authors.author_id, authors.name, pub_info.first_pub, pub_info.last_pub 
    from (select author_id, min(publication_year) as first_pub, max(publication_year) as last_pub from authored_book
        join books on authored_book.bib_number = books.bib_number
        where author_id in ({authors_list})
        group by author_id) as pub_info
        join authors
        on authors.author_id = pub_info.author_id
    """
    data = _connection.query(query)
    return data

def get_authors_ratings(_connection, authors_list):
    query = f"""
        select authors.author_id, authors.name, authors_avg.month, authors_avg.avg_rating, authors_avg.count_rating from
        (select authored_book.author_id, substr(reviews.date, 0, 7) as month, avg(reviews.rating) as avg_rating, count(reviews.rating) as count_rating from authored_book
            join reviews
            on reviews.bib_number = authored_book.bib_number
            where author_id in ({authors_list})
            group by authored_book.author_id, month) as authors_avg
            join authors on authors.author_id = authors_avg.author_id
            order by authors_avg.month desc, author_id
    """
    data = _connection.query(query)
    return data

def get_authors_checkouts(_connection, authors_list):
    query = f"""
    select authors.author_id, authors.name, checkouts.month, sum(checkouts.checkouts) as checkouts
        from authors
        join authored_book on authors.author_id = authored_book.author_id
        join checkouts on checkouts.bib_number = authored_book.bib_number
        where authors.author_id in ({authors_list})
        group by authors.author_id, authors.name, checkouts.month
        order by checkouts.month desc, authors.author_id
    """
    data = _connection.query(query)
    return data

def get_books_by_authors(_connection, authors_list):
    query = f"""
    select authors.author_id, authors.name, books.bib_number, books.title, books.publication_year, checkouts_agg.checkouts, reviews_agg.avg_rating, reviews_agg.rating_count
        from 
        (select authored_book.bib_number, authored_book.author_id, avg(reviews.rating) as avg_rating, count(reviews.rating) as rating_count
        from authored_book
        left outer join reviews
        on reviews.bib_number = authored_book.bib_number
        where author_id in ({authors_list})
        group by authored_book.bib_number, authored_book.author_id) as reviews_agg
        left outer join
        (select authored_book.bib_number, sum(checkouts.checkouts) as checkouts
        from authored_book
        left outer join checkouts
        on checkouts.bib_number = authored_book.bib_number
        where author_id in ({authors_list})
        group by authored_book.bib_number) as checkouts_agg
        on reviews_agg.bib_number = checkouts_agg.bib_number
        join books on reviews_agg.bib_number = books.bib_number
        join authors on authors.author_id = reviews_agg.author_id
    """
    data = _connection.query(query)
    return data
    


column_configuration = {
    "AUTHOR_ID": st.column_config.NumberColumn("Author ID", help="The ID of the author", 
                            format="%d"),
    "NAME": st.column_config.TextColumn(
        "Author Name",
        help="The name of the author",
        max_chars=100,
        width="medium"
    ),
    "TOTAL_CHECKOUTS": st.column_config.NumberColumn(
        "Total Checkouts",
        help="Total checkouts of books written by the author",
        width="medium",
    ),
    "FIRST_PUB": st.column_config.TextColumn(
        "Active from"
    ),
    "LAST_PUB": st.column_config.TextColumn(
        "Active to"
    ),
    "BIB_NUMBER":st.column_config.TextColumn(
        "Bib Number"
    ),
    "TITLE":st.column_config.TextColumn(
        "Book Title",
        width="large"
    ),

}

if 'selected' not in st.session_state:
    st.session_state.selected = pd.DataFrame()


select, works, compare = st.tabs(["Select Authors", "Authors Info", "Compare Authors"])
# Get the current credentials
session = st.connection("snowflake")


with select:
    st.header("Search Authors")


    search_author = st.text_input("Author Name or ID",
        placeholder='Author Name or ID',
    )

    df = search_authors_with_checkouts(session, search_author)

    authors = st.dataframe(
        df,
        column_config=column_configuration,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
    )

    st.header("Selected authors")
    selected_authors = authors.selection.rows
    st.session_state.selected = pd.concat([st.session_state.selected, df.iloc[selected_authors].copy()]).drop_duplicates()

    st.dataframe(
        st.session_state.selected,
        column_config=column_configuration,
        use_container_width=True,
        hide_index=True
    )

    if st.button("Clear"):
        authors.selection.rows = None
        st.session_state.selected = pd.DataFrame()
        st.rerun()

with works:
    authors_list = to_list(st.session_state.selected.AUTHOR_ID)
    if(len(authors_list) < 1):
        st.warning('You must select at least one author')
        st.stop()
    
    st.subheader("Authors first and last publication year")
    activity_df = get_authors_active_years(session, authors_list)
    st.dataframe(
        activity_df,
        column_config=column_configuration,
        use_container_width=True,
        hide_index=True
        )
    
    st.subheader("Books By Author")
    books_by_authors_df = get_books_by_authors(session, authors_list)
    st.dataframe(
        books_by_authors_df,
        column_config=column_configuration,
        use_container_width=True,
        hide_index=True
        )

    
    st.subheader("Authors Monthly Ratings")
    authors_ratings_df = get_authors_ratings(session, authors_list)
    st.dataframe(
        authors_ratings_df,
        column_config=column_configuration,
        use_container_width=True,
        hide_index=True
        )
    
    st.subheader("Authors Monthly Checkouts")
    authors_checkouts_df = get_authors_checkouts(session, authors_list)
    st.dataframe(
        authors_checkouts_df,
        column_config=column_configuration,
        use_container_width=True,
        hide_index=True
        )

with compare:
    authors_list = to_list(st.session_state.selected.AUTHOR_ID)
    if(len(authors_list) < 1):
        st.warning('You must select at least one author')
        st.stop()
    
    books_by_authors_df = get_books_by_authors(session, authors_list)
    authors_ratings_df = get_authors_ratings(session, authors_list)
    authors_checkouts_df = get_authors_checkouts(session, authors_list)
    
    authors_books_count = books_by_authors_df[['AUTHOR_ID', 'NAME', 'BIB_NUMBER']].groupby(by=['AUTHOR_ID', 'NAME']).count().reset_index().sort_values(by=['BIB_NUMBER'])
    st.subheader("Books By Author")
    st.bar_chart(
        authors_books_count,
        x='NAME',
        y='BIB_NUMBER',
        x_label='Author Name',
        y_label='Book Count',
        color=get_colors(1)
    )

    min_rating_month = authors_ratings_df.MONTH.min()
    max_rating_month = authors_ratings_df.MONTH.max()
    rating_daterange = get_daterange(min_rating_month, max_rating_month)

    st.subheader("Authors Monthly Ratings")
    oldest_year, oldest_month = divide_month(min_rating_month)
    newest_year, newest_month = divide_month(max_rating_month)
    year_range = range(oldest_year, newest_year + 1)

    col = st.columns(4)
    with col[0]:
        from_year = st.selectbox("From year", year_range, key='CA-C-RFY')
    with col[1]:
        first_month = oldest_month if from_year == oldest_year else 1
        last_month = newest_month if from_year == newest_year else 12
        from_month = st.selectbox("From month", range(first_month, last_month + 1), key='CA-C-RFM')
    with col[2]:
        to_year = st.selectbox("To year", year_range, index=len(year_range)-1, key='CA-C-RTY')
    with col[3]:
        first_month = oldest_month if to_year == oldest_year else 1
        last_month = newest_month if to_year == newest_year else 12
        to_month_range = range(first_month, last_month + 1)
        to_month = st.selectbox("To month", to_month_range, index=len(to_month_range) - 1, key='CA-C-RTM')
    
    from_date = join_month(from_year, from_month)
    to_date = join_month(to_year, to_month)

    rating_series_df = authors_ratings_df[(authors_ratings_df.MONTH >= from_date) & (authors_ratings_df.MONTH <= to_date)].groupby(by=['NAME', 'MONTH']).mean().reset_index()
    # rating_series_df = pd.pivot_table(authors_ratings_df, values='AVG_RATING', aggfunc='mean', index=['NAME', 'MONTH'] ).reset_index()
    st.line_chart(
        rating_series_df.pivot(index='MONTH', columns='NAME', values='AVG_RATING').sort_values(by='MONTH')
    )
    
    st.subheader("Authors Monthly Checkouts")
    min_checkouts_month = authors_checkouts_df.MONTH.min()
    max_checkouts_month = authors_checkouts_df.MONTH.max()
    checkouts_daterange = get_daterange(min_checkouts_month, max_checkouts_month)

    oldest_year_c, oldest_month_c = divide_month(min_checkouts_month)
    newest_year_c, newest_month_c = divide_month(max_checkouts_month)
    year_range_c = range(oldest_year_c, newest_year_c + 1)

    col = st.columns(4)
    with col[0]:
        from_year_c = st.selectbox("From year", year_range_c, key='CA-C-CFY')
    with col[1]:
        first_month_c = oldest_month_c if from_year_c == oldest_year_c else 1
        last_month_c = newest_month_c if from_year_c == newest_year_c else 12
        from_month_c = st.selectbox("From month", range(first_month_c, last_month_c + 1), key='CA-C-CFM')
    with col[2]:
        to_year_c = st.selectbox("To year", year_range_c, index=len(year_range_c)-1, key='CA-C-CTY')
    with col[3]:
        first_month_c = oldest_month_c if to_year_c == oldest_year_c else 1
        last_month_c = newest_month_c if to_year_c == newest_year_c else 12
        to_month_range_c = range(first_month_c, last_month_c + 1)
        to_month_c = st.selectbox("To month", to_month_range_c, index=len(to_month_range_c) - 1, key='CA-C-CTM')
    
    from_date_c = join_month(from_year_c, from_month_c)
    to_date_c = join_month(to_year_c, to_month_c)

    checkouts_series_df = authors_checkouts_df[(authors_checkouts_df.MONTH >= from_date_c) & (authors_checkouts_df.MONTH <= to_date_c)].groupby(by=['NAME', 'MONTH']).sum().reset_index()
    # checkouts_series_df = pd.pivot_table(authors_checkoutss_df, values='AVG_checkouts', aggfunc='mean', index=['NAME', 'MONTH'] ).reset_index()
    st.line_chart(
        checkouts_series_df.pivot(index='MONTH', columns='NAME', values='CHECKOUTS').sort_values(by='MONTH')
    )
