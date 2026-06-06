const mysql = require("mysql2");

const db = mysql.createConnection({
  host: "localhost",
  user: "root",
  password: "@Master5725#",
  database: "urbancab"
});

module.exports = db;