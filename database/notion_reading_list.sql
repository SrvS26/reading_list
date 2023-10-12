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
            user_id VARCHAR(255) NOT NULL PRIMARY KEY,
            num_books INT,
            num_books_unfilled INT,
            goodreads_status VARCHAR (255),
            is_processed INT DEFAULT 0 NOT NULL,
            FOREIGN KEY(user_id) REFERENCES USERS(user_id)
);  

CREATE TABLE IF NOT EXISTS GOODREADS_BOOKS (
            goodreads_id CHAR PRIMARY KEY,
            ISBN_10 CHAR,
            ISBN_13 CHAR,
            ASIN CHAR,
            title CHAR,
            author CHAR,
            series CHAR,
            issue VARCHAR,
            summary CHAR,
            goodreads_image_link CHAR,
            genre CHAR,
            pages INT,
            format CHAR,
            published_date CHAR,
            language CHAR,
            published_by CHAR,
            edition CHAR,
            image_link CHAR
);

CREATE TABLE IF NOT EXISTS VERSIONS(
            user_id VARCHAR(255),
            version CHAR,
            FOREIGN KEY(user_id) REFERENCES USERS(user_id)
);

CREATE TABLE IF NOT EXISTS TIER(
            license_key VARCHAR(255),
            start_date VARCHAR(255),
            expiry_date VARCHAR(255),
            FOREIGN KEY(license_key) REFERENCES USERS
);


CREATE TABLE IF NOT EXISTS GUMROAD(
            sale_id VARCHAR(255),
            sale_timestamp VARCHAR(255),
            order_number VARCHAR(255),
            product_id VARCHAR(255),
            permalink VARCHAR(255),
            product_permalink VARCHAR(255),
            product_name VARCHAR(255),
            short_product_id VARCHAR(255),
            email VARCHAR(255),
            full_name VARCHAR(255),
            subscription_id VARCHAR(255),
            ip_country VARCHAR(255),
            referrer VARCHAR(255),
            price VARCHAR(255),
            variants VARCHAR(255),
            is_recurring_charge VARCHAR(255),
            license_key VARCHAR(255),
            affiliate VARCHAR(255),
            affiliate_credit VARCHAR(255),
            refunded VARCHAR(255),
            discover_fee_charged VARCHAR(255),
            gumroad_fee VARCHAR(255),
            is_used INT DEFAULT 0,
            FOREIGN KEY(license_key) REFERENCES USERS
);
PRAGMA foreign_keys = ON;