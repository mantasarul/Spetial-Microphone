const fs = require("fs");
const cp = require("child_process");
const readline = require("readline");
const {google} = require("googleapis");
const sqlite3 = require("better-sqlite3");
const db = new sqlite3("craig.db");
db.pragma("journal_mode = WAL");

if (process.argv.length !== 6) process.exit(1);
const uid = process.argv[2];
const rid = process.argv[3];
const features = JSON.parse(process.argv[4]);
const info = JSON.parse(process.argv[5]);

const SCOPES = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive.metadata.readonly"];


fs.readFile(process.env.HOME + "/craig-drive/client_secret.json", (err, content) => {
    if (err) return console.error("Error loading client secret file:", err);
   
    authorize(JSON.parse(content), findUploadDir);
});


function authorize(credentials, callback) {
    const {client_secret, client_id, redirect_uris} = credentials.web;
    const oAuth2Client = new google.auth.OAuth2(
        client_id, client_secret, redirect_uris[0]);

    
    var row = db.prepare("SELECT * FROM drive WHERE id=?").get(uid);
    if (!row) return;
    oAuth2Client.setCredentials(JSON.parse(row.data));
    if (oAuth2Client.isTokenExpiring()) {
        oAuth2Client.refreshToken().then((newToken) => {
            fs.writeFile(TOKEN_PATH, JSON.stringify(newToken), ()=>{});
            callback(oAuth2Client, row);
        }).catch(()=>{});
    } else {
        callback(oAuth2Client, row);
    }
}


function findUploadDir(auth, row) {
    const drive = google.drive({version: "v3", auth});
    const opts = {
        pageSize: 1000,
        fields: "nextPageToken, files(id, name)",
        q: "mimeType = 'application/vnd.google-apps.folder'"
    };
    var files = [];
    drive.files.list(opts, page);
    
    function page(err, data) {
        if (err) return console.error("The API returned an error: " + err);
        data = data.data;
        files = files.concat(data.files);
        if (data.nextPageToken) {
            opts.pageToken = data.nextPageToken;
            drive.files.list(opts, page);
        } else {
            complete();
        }
    }

    function complete() {
        var craigDir = files.find((file) => {
            return (file.name.toLowerCase() === "craig");
        });
        if (craigDir) {
            upload(drive, craigDir, row);
        } else {
            drive.files.create({
                resource: {"name": "Craig", "mimeType": "application/vnd.google-apps.folder"},
                fields: "id"
            }, function (err, craigDir) {
                if (err) {
                    console.error("Failed to create Craig directory: " + err);
                } else {
                    upload(drive, craigDir.data, row);
                }
            });
        }
    }
}


function upload(drive, craigDir, row) {
    
    var format = "flac";
    if (row.format)
        format = row.format;
    var container = "zip";
    if (row.container)
        container = row.container;

    var ext = "zip";
    var mime = "application/zip";
    if (row.container === "exe") {
        ext = "exe";
        mime = "application/vnd.microsoft.portable-executable";
    }

   
    var cook = cp.spawn("./cook.sh", [rid, format, container], {
        stdio: ["ignore", "pipe", "ignore"]
    });
    drive.files.create({
        resource: {
            "name": info.startTime + "-" + info.channel.replace(/#.*/, "") + "-" + rid + "." + ext,
            "parents": [craigDir.id]
        },
        media: {"mimeType": mime, "body": cook.stdout}
    }, function (err, file) {
        if (err)
            console.error("Error upload: " + err);
        process.exit(0);
    });
}