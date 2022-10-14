CREATE TABLE IF NOT EXISTS USERS (
            access_token VARCHAR(255) NOT NULL,
            database_id VARCHAR(255) NOT NULL,
            bot_id VARCHAR(255) NOT NULL,
            workspace_name VARCHAR(255) NOT NULL,
            workspace_id VARCHAR(255) NOT NULL,
            owner_type VARCHAR(255) NOT NULL,
            user_id VARCHAR(255) NOT NULL PRIMARY KEY,
            user_name VARCHAR(255) NOT NULL,
            user_email VARCHAR(255) NOT NULL,
            time_added FLOAT NOT NULL,
            license_key VARCHAR(255),
            is_validated INT DEFAULT 0 NOT NULL,
            is_revoked INT DEFAULT 0 NOT NULL
            -- PRIMARY KEY (database_id, user_id)
            );


CREATE TABLE IF NOT EXISTS IMAGES (
            ISBN_10 VARCHAR(255),
            ISBN_13 VARCHAR(255),
            image_path VARCHAR(255) NOT NULL
);


-- ALTER TABLE USERS ADD COLUMN user_status VARCHAR(255);

CREATE TABLE IF NOT EXISTS GOODREADS (
            database_id VARCHAR(255),
            user_id VARCHAR(255),
            num_books INT,
            num_books_unfilled INT,
            goodreads_status VARCHAR (255),
            is_processed INT DEFAULT 0 NOT NULL,
            FOREIGN KEY(user_id) REFERENCES USERS(user_id)
);  

-- CREATE TABLE IF NOT EXISTS GOODREADS_BOOKS (
--             new_id CHAR,
--             goodreads_id CHAR,
--             ISBN_10 CHAR,
--             ISBN_13 CHAR,
--             ASIN CHAR,
--             title CHAR,
--             author CHAR,
--             series CHAR,
--             issue VARCHAR,
--             summary CHAR,
--             goodreads_image_link CHAR,
--             genre CHAR,
--             pages INT,
--             format CHAR,
--             published_date CHAR,
--             language CHAR,
--             published_by CHAR,
--             edition CHAR,
--             image_link CHAR
-- )

PRAGMA foreign_keys = ON;