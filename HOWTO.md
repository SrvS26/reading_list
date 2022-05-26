# Notion Reading List

## Generating an SSH Keypair

Use the following command to create an SSH keypair. This will create a pair of public and private keys. The public key will be added to the remote server and when we login:

`$ ssh-keygen -t rsa -C "yourname@machinename"`

Both values are for our own differentiation and is not important for the server.

- `yourname` - to differentiate your key
- `machinename` - to identify which machine you are creating this key for

- Now the command will suggest a path where the files will be generated. You can let the path be default and press enter.
- It now asks for a passphrase to be entered. You will have to enter it twice.
- Once you have entered the passphrase it will generate the keypair in the default location.
- Share the public key so you can be added to the server.

## Logging in to the server

You can now login to the server with the private key using:

`$ ssh -i ~/.ssh/id_rsa se7enforward@40.79.241.95 -t "tmux attach"`

- `-i` - the location of the private key file
- `se7enforward` - the user on the remote server
- `x.x.x.x` - the IP address of the remote server
- `-t` - the command to run on the remote server. In our case the command is `tmux attach`. This will give you a way to open multiple terminals in the remote server without having to login every time.

## Making sense of what's on the screen

You are now presented with a bottom bar with a few numbers and items.

- The numbers denote how many terminals are open and the `*` at the end of the command denotes which terminal is active at the moment.
- You can switch terminals using `Ctrl + b` + `<num>`. If you are on terminal 0 and need to switch to terminal 1, you can switch using `Ctrl + b` + `1` and similarly.
- To switch between panes, you can use `Ctrl + b` + `<arrow_key>`.

### Terminal 0

#### Pane 1

`ReadingList.py` runs here. If you have any changes, you can switch to this pane and stop it and run it again as you would normally do with the virtual environment already activated.

#### Pane 2

Live logs for `nginx` are shown here. Any request that someone makes to `https://seven-forward.com` or the public IP address will be shown here with their IP address, time of request, what they tried to access (request method and route), the status code that nginx responded with, etc.

### Terminal 1 & 2

These terminals are for any other operations we want to perform.

## How to do a new release

Let's say you have updated some code and pushed to GitHub and would like to deploy your new shiny feature or a bug fix.

- Switch to the directory: `cd ~/reading_list`
- Check if there's any new changes on GitHub: `git fetch` and then `git pull`
- Once you have your latest changes, you can restart the respective programs using:  
`ReadingList.py`: switch to the terminal where it's running and stop it and re-run it via `python ReadingList.py`  
`publicInteg.py`: this is run via `uWSGI` with a system service. You can restart the service via `sudo systemctl restart publicInteg` and check for the status using `sudo systemctl status publicInteg` which should say: `active(running)`

## Location for important items

### nginx

- config: `/etc/nginx/sites-available/seven-forward`
- access logs: `/var/log/nginx/access.log`

### ReadingList

- app log: `~/reading_list/app/app.log`
- server log: `~/reading_list/server/server.log`

## Exiting the server

You can use `Ctrl + b` + `d` to exit the SSH connection.
