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

