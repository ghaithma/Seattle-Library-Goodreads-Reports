import numpy as np
import pandas as pd
import streamlit as st
from snowflake.snowpark.context import get_active_session


def to_list(series):
    return ",".join(list(series.astype(str)))

@st.cache_data
def search_authors_with_checkouts(_session, author_name, query_limit=10):
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
    data = _session.sql(query).collect()
    return pd.DataFrame(data)

def get_authors_active_years(_session, authors_list):
    query = f"""
    select authors.author_id, authors.name, pub_info.first_pub, pub_info.last_pub 
    from (select author_id, min(publication_year) as first_pub, max(publication_year) as last_pub from authored_book
        join books on authored_book.bib_number = books.bib_number
        where author_id in ({authors_list})
        group by author_id) as pub_info
        join authors
        on authors.author_id = pub_info.author_id
    """
    data = _session.sql(query).collect()
    return pd.DataFrame(data)

def get_authors_ratings(_session, authors_list):
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
    data = _session.sql(query).collect()
    return pd.DataFrame(data)

def get_authors_checkouts(_session, authors_list):
    query = f"""
    select authors.author_id, authors.name, checkouts.month, sum(checkouts.checkouts) as checkouts
        from authors
        join authored_book on authors.author_id = authored_book.author_id
        join checkouts on checkouts.bib_number = authored_book.bib_number
        where authors.author_id in ({authors_list})
        group by authors.author_id, authors.name, checkouts.month
        order by checkouts.month desc, authors.author_id
    """
    data = _session.sql(query).collect()
    return pd.DataFrame(data)

def get_books_by_authors(_session, authors_list):
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
    data = _session.sql(query).collect()
    return pd.DataFrame(data)
    


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
session = get_active_session()


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
    authors_ratings_df = get_authors_checkouts(session, authors_list)
    st.dataframe(
        authors_ratings_df,
        column_config=column_configuration,
        use_container_width=True,
        hide_index=True
        )

with compare:
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
    authors_ratings_df = get_authors_checkouts(session, authors_list)
    st.dataframe(
        authors_ratings_df,
        column_config=column_configuration,
        use_container_width=True,
        hide_index=True
        )
    # activity_df = {}
    # for person in selected_authors:
    #     activity_df[df.iloc[person]["name"]] = df.iloc[person]["activity"]
    # activity_df = pd.DataFrame(activity_df)

    # daily_activity_df = {}
    # for person in selected_authors:
    #     daily_activity_df[df.iloc[person]["name"]] = df.iloc[person]["daily_activity"]
    # daily_activity_df = pd.DataFrame(daily_activity_df)

    # if len(selected_authors) > 0:
    #     st.header("Daily activity comparison")
    #     st.bar_chart(daily_activity_df)
    #     st.header("Yearly activity comparison")
    #     st.line_chart(activity_df)
    # else:
    #     st.markdown("No members selected.")
