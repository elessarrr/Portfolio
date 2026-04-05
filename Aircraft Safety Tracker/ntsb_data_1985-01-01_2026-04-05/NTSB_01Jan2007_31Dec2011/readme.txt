Run time: 05/04/2026 11:36:37

Json query: {"ExportFormat":"data","ResultSetSize":500,"ResultSetOffset":9500,"TargetCollection":"cases","AndOr":"And","QueryGroups":[{"AndOr":"And","QueryRules":[{"RuleType":0,"Values":["Aviation"],"Columns":["Event.Mode"],"Operator":"contains"},{"RuleType":0,"Values":["2007-01-01","2011-12-31"],"Columns":["Event.EventDate"],"Operator":"is in the range"}]}],"SortColumn":null,"SortDescending":true,"SessionId":241452}

Query text: [
	(Mode) contains (Aviation)
	And
	(EventDate) is in the range (2007-01-01 OR 2011-12-31)
]

