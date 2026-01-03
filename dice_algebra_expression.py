from random import randint

def roll_dice(count:int, die_type:int):
    accum:int = 0
    for i in range(count):
        accum += randint(1, die_type)
    print(f"rolled {count}d{die_type}")
    return accum

# def roll_exploding_dice(count:int, die_type:int):
#     accum:int = 0
#     for i in range(count):

# class ExpressionParameter:
#     def __init__(self, identifier:str, value) :
#         self.identifier = identifier
#         self.value = value

# TODO remove "_" from the ignored character list... we should free it up for use in parameters only or something?
# TODO IMPORTANT force parameter identifiers to be all-caps!

class Expression:
    '''Represents a die algebra expression with variable parameters.'''
    def __init__(self, expression:str="", parameters:dict[str, int]=dict()):
        self.expression:str = expression
        self.parameters:dict[str,int] = parameters

    def get_parameter(self, parameter_identifier:str) -> int|None:
        '''Returns None if the identifier is not one of the parameters supplied in this Expression.'''
        if parameter_identifier in self.parameters.keys():
            return self.parameters[parameter_identifier]
        else:
            return None

    def set_parameter(self, parameter_identifier:str, parameter_value:int) -> bool:
        '''returns whether the operation succeeded. Does not create new parameters.'''
        succeeded:bool = parameter_identifier in self.parameters.keys()
        if succeeded:
            self.parameters[parameter_identifier] = parameter_value
        return succeeded

    def add_parameter(self, parameter_identifier:str) -> bool:
        '''Creates a new parameter, if it did not exist before, and sets its value to 0.'''
        succeeded: bool = not (parameter_identifier in self.parameters.keys())
        if succeeded:
            self.parameters[parameter_identifier] = 0
        return succeeded

    def evaluate(self):
        '''Interprets this die algebra expression.'''
        accum:int = 0
        die_count:int = 0
        current_number:int = 0
        idx:int = 0
        negative:bool = False
        current_block_is_valid:bool = False
        exploding = False
        previously_processed_character:str = None
        explicitly_ignore_this_character:str = False

        # TODO make sure subbed_expression is a COPY when changes occur... if internment occurs, make sure it causes no issues!
        subbed_expression = self.expression

        # TODO IMPORTANT make sure the parameters are sorted such that longest identifiers go first! This will PREVENT COLLISIONS!
        # TODO write a test in the file for this! Make sure you test that you CAN write code that violates it first, THEN solve it!
        # TODO WE NEED TO MAKE SURE WE CAN SOLVE THIS PROBLEM, BECAUSE WE HAVE NO GUARANTEE WHAT ORDER ITEMS ARE IN A DICTIONARY
        # TODO Read the Python docs on dictionaries.
        # SUB IN PARAMETER VALUES FOR EACH PARAMETER IDENTIFIER THAT APPEARS
        identifiers_list:list[str] = [iden for iden in self.parameters.keys()]
        identifiers_list.sort()
        for identifier in identifiers_list:
            subbed_expression.replace(identifier, subbed_expression.parameters[identifier])
            print(f"replaced {identifier} with {subbed_expression.parameters[identifier]}") # is debug :P

        # EVALUATE DIE EXPRESSION
        while idx < len(subbed_expression):
            character = subbed_expression[idx]
            match character:
                case '+' | '-' :
                    # since + and - are intended to start new blocks, we'll need to process the
                    # current block, if it's valid.
                    # MAINTENANCE NOTE: the code in this if-case is duplicated at the end of this function. Duplicate changes made here to there as well.
                    if current_block_is_valid:
                        # if no 'd' has been included...
                        # NOTE whenever 'd' is written before any digits have been specified,
                        # `die_count` is set to 1 by default. Therefore, if `die_count` is 0,
                        # then we know we are just handling a flat number.
                        v=0
                        if die_count == 0:
                            v = current_number
                        else:
                            if exploding:
                                pass # TODO
                            else:
                                v = roll_dice(die_count, current_number)
                        # apply the block to our accumulator with the appropriate sign
                        if negative:
                            accum += -v
                        else:
                            accum += v
                        negative = False
                    # wipe the current block
                    die_count = 0
                    current_number = 0
                    current_block_is_valid = False
                    exploding = False
                    negative = (character == '-')
                case 'd':
                    if previously_processed_character and (
                        previously_processed_character == 'd' or
                        previously_processed_character == '%' or
                        previously_processed_character == '!' ):
                        print("'d' is not a valid character immediately following 'd', '%', or '!' in a dice expression.");
                        print(f"Caused by character \'{character}\' at index [{idx}] in expression = \"{subbed_expression}\"")
                        return None
                    if current_block_is_valid:
                        die_count = current_number
                        current_number = 0
                    else:
                        die_count = 1
                    # blocks must explicitly end with a number to be valid!
                    current_block_is_valid = False
                case '0':
                    if current_block_is_valid:
                        current_number *= 10
                    else:
                        # ignore 0's which do not follow other digits.
                        pass
                case '1' | '2' | '3' | '4' | '5' | '6' | '7' | '8' | '9':
                    if current_block_is_valid:
                        current_number *= 10
                    else:
                        current_block_is_valid = True
                    # Add the digit to our current number.
                    current_number += int(character)

                ## SPECIAL CHARACTERS
                case '%':
                    # make sure the previously processed character was a 'd'.
                    if previously_processed_character and previously_processed_character == 'd':
                        current_number = 100
                        current_block_is_valid = True
                    # NOTE it's important to note that a user can follow a % with whatever they'd like.
                    # NOTE E.g., "2d%55" would be equivalent to "2d10055".
                    else:
                        print("A percentile '%' symbol may only follow a 'd', to indicate a percentile die. "
                              "For example, \"1d%\" would be valid, and equivalent to \"1d100\".")
                        print(f"Caused by character \'{character}\' at index [{idx}] in expression = \"{subbed_expression}\"")
                        return None
                case '!':
                    if current_block_is_valid and die_count > 0:
                        exploding = True
                case '_' | ' ' | '\t':
                    explicitly_ignore_this_character = True
                case _:
                    print("An unrecognized character was rejected from die expression.")
                    print("The only valid characters in dice expressions are the numerals 0-9, "
                          "the operators '+', '-', 'd', '%', '!' and the inert or white-space "
                          "characters '_', ' ', and '\\t'.")
                    print(f"Caused by character \'{character}\' at index [{idx}] in expression = \"{subbed_expression}\"")
                    return None
            if not explicitly_ignore_this_character:
                previously_processed_character = character
            explicitly_ignore_this_character = False
            # Increment idx
            idx += 1
        # Process any remaining block
        # MAINTENANCE NOTE: the code in this if-case is duplicated at the beginning of the function's match case. Duplicate changes made here to there as well.
        if current_block_is_valid:
            # if no 'd' has been included...
            # NOTE whenever 'd' is written before any digits have been specified,
            # `die_count` is set to 1 by default. Therefore, if `die_count` is 0,
            # then we know we are just handling a flat number.
            v = 0
            if die_count == 0:
                v = current_number
            else:
                if exploding:
                    pass  # TODO
                else:
                    v = roll_dice(die_count, current_number)
            # apply the block to our accumulator with the appropriate sign
            if negative:
                accum += -v
            else:
                accum += v
            negative = False

        # Successfully return the answer
        return accum