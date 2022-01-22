-- Creating the base schema.
CREATE TABLE bot_lines(
    name VARCHAR(64) PRIMARY KEY NOT NULL,
    bot_text TEXT NOT NULL,
    defines VARCHAR(64));

CREATE TABLE flows(
    source VARCHAR(64) NOT NULL,
    target VARCHAR(64) NOT NULL,
    answer VARCHAR(64),
    FOREIGN KEY(source) REFERENCES bot_lines(name),
    FOREIGN KEY(target) REFERENCES bot_lines(name));
