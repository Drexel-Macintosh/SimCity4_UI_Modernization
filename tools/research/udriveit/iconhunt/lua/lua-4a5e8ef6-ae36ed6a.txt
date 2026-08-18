--#-package:0454ce10# -- package signature --
-- Any Lua files that depend on this file must have higher package numbers.

dofile("adv_game_data.lua") -- for the game and sc4game tables

---------------------------------------------------------------------------------
-- dbpf table
---------------------------------------------------------------------------------

dbpf = {}

-- Reads the specified cohort property.
-- The group_id, instance_id, and property_id values must be a number, convert hexadecimal strings to a number with the hex2dec function.
-- The returned type will depend on the property type.
-- Nil is returned if the cohort/property does not exist.
dbpf.get_cohort_property_value = function(group_id, instance_id, property_id) return nil end

-- Reads the specified exemplar property.
-- The group_id, instance_id, and property_id values must be a number, convert hexadecimal strings to a number with the hex2dec function.
-- The returned type will depend on the property type.
-- Nil is returned if the exemplar/property does not exist.
dbpf.get_exemplar_property_value = function(group_id, instance_id, property_id) return nil end

-- Gets a value indicating if the specified TGI exists in the game.
-- The type_id, group_id, and instance_id values must be a number, convert hexadecimal strings to a number with the hex2dec function.
dbpf.resource_exists = function(type_id, group_id, instance_id) return false end

---------------------------------------------------------------------------------
-- game table extensions
---------------------------------------------------------------------------------

-- Executes the specified cheat code or command.
-- Takes a single string parameter.
-- The return value will vary depending on the input string:
--   1. A valid cheat code will return a Boolean (true or false).
--   2. A string that is not recognized as a valid cheat code or command will
--	    return the Boolean value false.
--   3. Commands will return various values, Boolean, numbers, arrays, strings, etc.
game.execute_cheat = function(cheat_string) return false end

-- Pauses the game.
game.pause = function() end

-- Resumes the game.
game.resume = function() end

---------------------------------------------------------------------------------
-- sc4game table extensions
---------------------------------------------------------------------------------
-- The GameDataRegistry class that is used to register the sc4game methods appears to
-- have been intended as a way for C++ classes to add lua functions, it allows a 
-- pointer to the class to be stored as user data for the function.

-- budget table - Maxis already defined this

-- Gets the total expense for the specified budget department.
-- The department_guid must be a number, convert hexadecimal strings to a number with the hex2dec function.
sc4game.budget.get_department_total_expense = function(department_guid) return 0 end

-- Gets the total income for the specified budget department.
-- The department_guid must be a number, convert hexadecimal strings to a number with the hex2dec function.
sc4game.budget.get_department_total_income = function(department_guid) return 0 end

-- language table

sc4game.language = {}

  -- Gets a value indicating if left-hand drive (LHD) is in use for the current language.
  -- This is true for UKEnglish and Japanese; otherwise, false.
  sc4game.language.is_left_hand_drive = function() return false end
  
  -- Gets a value indicating if the last name precedes the first name.
  sc4game.language.are_first_and_last_names_reversed = function() return false end
  
  -- Gets the currency symbol.
  -- This is always the 'Simolean' symbol, a UTF-8 encoded section sign.
  sc4game.language.get_currency_symbol = function() return "" end
  sc4game.language.does_currency_symbol_precede_amount = function() return false end
  sc4game.language.is_space_between_currency_symbol_and_amount = function() return false end
  
  -- Gets a string containing the decimal separator for the current language.
  sc4game.language.get_decimal_separator = function() return "" end
  -- Gets a string containing the thousands separator for the current language.
  sc4game.language.get_thousands_separator = function() return "" end  
  
  sc4game.language.get_date_string = function(month, day, year) return "" end  
 
  -- Converts a number to a money string.
  sc4game.language.get_money_string = function(number) return "" end
   
  -- Converts a number to a string using SC4's formatting code with
  -- the specified number of decimal places.
  sc4game.language.get_formatted_number_string = function(number, decimal_places) return "" end
  
  -- Converts a number to a string using SC4's formatting code.
  sc4game.language.get_number_string = function(number)
    return sc4game.language.get_formatted_number_string(number, 0)
  end

-- city table

sc4game_city_place_lot_orientation = {}
  sc4game_city_place_lot_orientation.NORTH = 0
  sc4game_city_place_lot_orientation.EAST = 1
  sc4game_city_place_lot_orientation.SOUTH = 2
  sc4game_city_place_lot_orientation.WEST = 3 

sc4game.city = {}

  -- Gets the city name as a UTF-8 string.  
  sc4game.city.get_city_name = function() return "" end
  
  -- Sets the city name.
  sc4game.city.set_city_name = function(new_city_name) end
  
  -- Gets the mayor name as a UTF-8 string.
  sc4game.city.get_mayor_name = function() return "" end
  
  -- Sets the mayor name.
  sc4game.city.set_mayor_name = function(new_mayor_name) end
  
  -- Constructs a lot at the the specified coordinates.
  -- This function requires SimCity 4 Deluxe version 641.
  -- The orientation parameter is a value from the sc4game_city_place_lot_orientation table. 
  -- The building_exemplar_iid parameter is optional unless you want a specific variant
  -- for a lot that is used by multiple building families.
  -- The lot_exemplar_iid and building_exemplar_iid must be a number, convert hexadecimal strings to a number with the hex2dec function.
  sc4game.city.place_lot = function(city_x, city_z, orientation, lot_exemplar_iid, building_exemplar_iid) return false end
  
-- camera table
  
sc4game.camera = {}

  -- Gets the cell the camera is focused on.
  -- Returns the X and Z cell coordinates.
  sc4game.camera.get_current_cell = function() return {} end
  
  -- Gets the cell the camera is focused on.
  -- Returns the X, Y (altitude), and Z cell coordinates.
  sc4game.camera.get_current_position = function() return {} end

  -- Moves the camera to the specified cell.
  sc4game.camera.jump_to_cell = function(cell_x, cell_z) end
  
  -- Moves the camera to the specified position.
  sc4game.camera.jump_to_position = function(x, y, z) end
  
  -- Rotates the camera in a clockwise direction.
  sc4game.camera.rotate_clockwise = function() end
  
  -- Rotates the camera in a counter-clockwise direction.
  sc4game.camera.rotate_counter_clockwise = function() end
  
  -- Takes a snapshot of the game window and saves it to the specified file.
  -- The area parameters are optional, when omitted the entire game window will be captured.
  sc4game.camera.take_snapshot = function(file_path, area_x, area_y, area_width, area_height) return false end

  