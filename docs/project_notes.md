# Project

# Data sources

## Library Inventory

Will split into two sections. Books Master data and timed inventory count

### Books Master data

- BibNum: Library system unique identifier (Will be used to link books with inventory counts)
- Title [Text]: repeated in Goodreads books collection
- Author [Text]: repeated in Goodreads books collection
- ISBN List: Will be split into a lookup of (BibNum - ISBN) linking to Goodreads dataset.
    
    It would be nice to apply cleaning rules on the ISBN (e.g. length, set of characters, regex)
    
- **PublicationYear: Not super clean. will probably use Goodreads publication year (if it’s always available)**
- **Publisher: Would be nice to have as a dimension, but we need to check Goodreads to find which is cleaner**
- 

- Goodreads Books
- Goodreads Authors
- Goodreads Reviews
- Goodreads Works

## Good reads

Mongodb commands:

db.reviews.aggregate([ { $sample: { size: 1 } } ])

### Books

We need to remove the books that are not in the library system. The approach we are using is to load the Goodreads book data into Pandas and then cleaning unneeded books.

- Dropped useless attributes: `db.books.updateMany({}, {$unset : { popular_shelves: "", asin: "", is_ebook: "", kindle_asin: "", similar_books: ""}})`
- Dropped records that had neither isbn nor isbn13
- Dropped records that did not exist in the library system

### Authors

- average_rating: Ignore? generating using our DWH (DWH Goal)
- author_id: used to link book, work and review
- text_reviews_count: Ignore?
- name: Display?
- ratings_count: DWH Goal

### Reviews

we have 15 million records. loading them into pandas is a challenge.

- The following attributes were dropped `db.reviews.updateMany({}, {$unset : { review_text: "", read_at: "", started_at: "", n_votes: "", n_comments: ""}})`
- 

[Project Plan](Project%201e8cad840d3980db8722c279497568be/Project%20Plan%201eacad840d3980ff99edec23afde55ae.md)