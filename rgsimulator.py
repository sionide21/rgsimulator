#!/usr/bin/python
import Tkinter
import tkSimpleDialog
import argparse
import game
import ast
import sys
import traceback
import os
import rg
import settings
from settings import AttrDict

class SimulatorUI:
	def __init__(self, settings, map, player):
		self.settings = settings
		self.map = map
		self.player = player

		self.center = rg.CENTER_POINT

		self.square_size = 40
		self.fill_color = "#FFF"
		self.obstacle_fill_color = "#555"
		self.enemy_fill_color = "#F00"
		self.teammate_fill_color = "#0F0"
		self.border_color = "#333"
		self.selection_border_color = "#FF0"

		self.map_width = settings.board_size
		self.map_height = settings.board_size
		self.width = self.square_size*self.map_width
		self.height = self.square_size*self.map_height

		self.root = Tkinter.Tk()
		self.root.resizable(0, 0)
		self.setTitle("Robot Game Simulator")

		self.turn_label = Tkinter.Label(self.root, text = "")
		self.turn_label.pack()
		self.setTurn(1)

		self.canvas = Tkinter.Canvas(self.root, width = self.width, height = self.height)
		self.canvas.pack()

		self.squares = {}
		self.labels = {}
		for x in xrange(0, self.map_width):
			for y in xrange(0, self.map_height):
				coordinates = self.getSquareCoordinates((x, y))
				x1, y1 = coordinates[0]
				x2, y2 = coordinates[1]

				self.squares[(x, y)] = self.canvas.create_rectangle(
					x1, y1, x2, y2,
					fill = self.obstacle_fill_color if self.isObstacle((x, y)) else self.fill_color,
					outline = self.border_color,
					width = 1
				)
				self.labels[(x, y)] =  self.canvas.create_text(
					x1 + self.square_size/2, y1 + self.square_size/2,
					text = (x+1)*(y+1)-1 if x*y == 0 else "", # the most clever hack I've ever did
					font = "TkFixedFont", 
					fill = "#000"
				)

		self.selection = self.center
		selection_coordinates = self.getSquareCoordinates(self.selection)
		selection_x1, selection_y1 = selection_coordinates[0]
		selection_x2, selection_y2 = selection_coordinates[1]
		self.selection_square = self.canvas.create_rectangle(
			selection_x1, selection_y1, selection_x2, selection_y2,
			fill = "",
			outline = self.selection_border_color,
			width = 5
		)

		self.robots = []
		self.field = game.Field(settings.board_size)
		self.robot_id = 0

		self.player

		self.root.bind("w", lambda ev: self.moveSelection((0, -1)))
		self.root.bind("a", lambda ev: self.moveSelection((-1, 0)))
		self.root.bind("s", lambda ev: self.moveSelection((0, 1)))
		self.root.bind("d", lambda ev: self.moveSelection((1, 0)))
		self.root.bind("<Up>", lambda ev: self.moveSelection((0, -1)))
		self.root.bind("<Left>", lambda ev: self.moveSelection((-1, 0)))
		self.root.bind("<Down>", lambda ev: self.moveSelection((0, 1)))
		self.root.bind("<Right>", lambda ev: self.moveSelection((1, 0)))

		self.root.bind("t", self.onEditTurn)
		self.root.bind("f", self.onAddTeammate)
		self.root.bind("e", self.onAddEnemy)
		self.root.bind("r", self.onRemove)
		self.root.bind("<Delete>", self.onRemove)
		self.root.bind("<BackSpace>", self.onRemove)
		self.root.bind("h", self.onEditHP)
		self.root.bind("<space>", self.onSimulate)
		self.root.bind("<Return>", self.onSimulate)

		self.root.mainloop()

	def getSquareCoordinates(self, loc):
		x, y = loc
		return (
			(self.square_size*x, self.square_size*y), 
			(self.square_size*(x + 1), self.square_size*(y + 1))
		)

	def isObstacle(self, loc):
		return loc in self.map['obstacle']

	def setSelection(self, loc):
		if not self.isObstacle(loc):
			selection_coordinates = self.getSquareCoordinates(loc)
			selection_x1, selection_y1 = selection_coordinates[0]
			selection_x2, selection_y2 = selection_coordinates[1]
			self.canvas.coords(self.selection_square, selection_x1, selection_y1, selection_x2, selection_y2)
			self.selection = loc

	def moveSelection(self, dloc):
		self.setSelection((self.selection[0] + dloc[0], self.selection[1] + dloc[1]))

	def setTitle(self, title):
		self.root.title(title)

	def setTurn(self, turn):
		self.turn = turn
		self.turn_label.config(text = "Turn %s" % self.turn)

	def setFill(self, loc, color):
		self.canvas.itemconfigure(self.squares[loc], fill = color)
	
	def setText(self, loc, text):
		self.canvas.itemconfigure(self.labels[loc], text = text)

	def onEditTurn(self, event):
		new_turn = tkSimpleDialog.askinteger(
			"Edit turn", "Enter new turn", 
			parent = self.root, 
			initialvalue = self.turn,
			minvalue = 1,
			maxvalue = 100
		)
		if new_turn is not None:
			self.setTurn(new_turn)

	def updateSquare(self, loc):
		robot = self.getRobot(loc)
		if robot is None:
			self.setFill(loc, self.fill_color)
			self.setText(loc, "")
		else:
			if robot.player_id == 1:
				self.setFill(loc, self.teammate_fill_color)
			else:
				self.setFill(loc, self.enemy_fill_color)

			self.setText(loc, robot.hp)


	def onRemove(self, event):
		if self.getRobot(self.selection) is not None:
			self.removeRobot(self.selection)

		self.updateSquare(self.selection)

	def onAddTeammate(self, event):
		if self.getRobot(self.selection) is not None:
			self.removeRobot(self.selection)

		self.addRobot(self.selection, 1)
		self.updateSquare(self.selection)

	def onAddEnemy(self, event):
		if self.getRobot(self.selection) is not None:
			self.removeRobot(self.selection)

		self.addRobot(self.selection, 0)
		self.updateSquare(self.selection)


	def onEditHP(self, event):
		robot = self.getRobot(self.selection)
		if robot is not None:
			new_hp = tkSimpleDialog.askinteger(
				"Edit hp", "Enter new hp", 
				parent = self.root, 
				initialvalue = robot.hp,
				minvalue = 1,
				maxvalue = 50
			)
			if new_hp is not None:
				robot.hp = new_hp
				self.updateSquare(self.selection)


	def getRobotID(self):
		ret = self.robot_id
		self.robot_id += 1
		return ret

	def removeRobot(self, loc):
		self.robots.remove(self.field[loc])
		self.field[loc] = None

	def getRobot(self, loc):
		return self.field[loc]

	def addRobot(self, loc, player_id):
		robot_id = self.getRobotID()
		robot = game.InternalRobot(loc, self.settings.robot_hp, player_id, robot_id, self.field)
		self.robots.append(robot)
		self.field[loc] = robot

	def buildGameInfo(self):
		return AttrDict({
			'robots': dict((
				y.location,
				AttrDict(dict(
					(x, getattr(y, x)) for x in
					(self.settings.exposed_properties + self.settings.player_only_properties)
				))
			) for y in self.robots),
			'turn': self.turn,
		})

	def getActions(self):
		self.player._robot = None
		game_info = self.buildGameInfo()
		actions = {}

		for robot in self.robots:
			if robot.player_id == 1:
				user_robot = self.player.get_robot()
				for prop in self.settings.exposed_properties + self.settings.player_only_properties:
					setattr(user_robot, prop, getattr(robot, prop))

				try:
					next_action = user_robot.act(game_info)
					if not robot.is_valid_action(next_action):
						raise Exception('Bot %d: %s is not a valid action from %s' % (robot.player_id + 1, str(next_action), robot.location))
				except Exception:
					traceback.print_exc(file = sys.stdout)
					next_action = ['guard']
				actions[robot] = next_action
		return actions

	def onSimulate(self, event):
		print(self.getActions())


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Robot game simulation script.")
	parser.add_argument(
		"usercode",
		help="File containing robot class definition."
	)
	parser.add_argument(
		"-m", "--map", 
		help="User-specified map file.",
		default=os.path.join(os.path.dirname(__file__), 'maps/default.py'))

	args = parser.parse_args()

	map_name = os.path.join(args.map)
	map_data = ast.literal_eval(open(map_name).read())
	game.init_settings(map_data)
	player = game.Player(open(args.usercode).read())

	SimulatorUI(settings.settings, map_data, player)
	