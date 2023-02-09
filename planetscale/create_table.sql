CREATE TABLE stats (
  id int NOT NULL AUTO_INCREMENT PRIMARY KEY,
  date varchar(255) UNIQUE NOT NULL,
  nap_count INT UNSIGNED,
  nap_minute FLOAT UNSIGNED,
  night_sleep_count INT UNSIGNED,
  night_sleep_minute FLOAT UNSIGNED,
  night_wakeup_count INT UNSIGNED,
  night_wakeup_minute FLOAT UNSIGNED,
  milk_count INT UNSIGNED,
  milk_ml FLOAT UNSIGNED,
  breastfeeding_count INT UNSIGNED,
  breastfeeding_minute FLOAT UNSIGNED,
  baby_food_count INT UNSIGNED,
  baby_food_minute FLOAT UNSIGNED,
  age_of_month INT UNSIGNED
);