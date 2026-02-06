users = [
  { id: 1, name: "ANNA", active: true },
  { id: 2, name: "BOB", active: false },
  { id: 3, name: "CHRIS", active: true }
]


function getActiveUsersInUpperCase(users) {
  return users.filter(user => user.active).map(user => user.name.toUpperCase());
}

getActiveUsersInUpperCase(users)