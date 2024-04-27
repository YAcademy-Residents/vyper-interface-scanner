import argparse
import subprocess

def remove_unwanted_lines_and_sort(multiline_text):
    lines = multiline_text.splitlines()
    # Exclude lines without "def" defining a function
    trimmed_text = '\n'.join(line for line in lines if line.find("def") > -1)
    return '\n'.join(sorted(trimmed_text.splitlines()))


def remove_custom_variable_names(multiline_text):
    output = ""
    # Loop through lines to remove variable names
    for line in multiline_text.splitlines():
        # Skip lines with interface definition, lines that define a function in the interface, lines that are comments, or empty lines
        if line.find("def ") > -1:
            function_args = line[line.find("(")+1:line.find(")")]
            if len(function_args) > 0: # if there are function args, remove the variable names
                split_args = function_args.split(",")
                for j in range(len(split_args)):
                    if split_args[j].find(":") > 0:
                        split_args[j] = split_args[j].split(":")[1].strip()
                function_args = ','.join(line for line in split_args)
                line = line[:line.find("(")+1] + function_args + line[line.find(")"):]
            output += line + "\n"
        else:
            output += line + "\n"
    return output

def compare_interfaces():
    parser = argparse.ArgumentParser(description="Run the script with: python interface-checker.py called_contract.vy caller_contract.vy interface_name")
    parser.add_argument("called_contract_path", help="This contract is called by the other contract. This contract holds the 'correct' implementation that the caller interface should align with")
    parser.add_argument("caller_contract_path", help="This contract stores the interface definition that attempts to match the called contract")
    parser.add_argument("interface_name", help="The name of the interface defined in caller_contract_path.vy")
    parser.add_argument("--strict", action=argparse.BooleanOptionalAction, help="Only print output when there is a confirmed issue, ignore possible false positives. Do not print DONE.")
    parser.add_argument("--skip-unused", action=argparse.BooleanOptionalAction, help="Skip checking for (low priority) unused interface definitions")
    parser.add_argument("--disable-color", action=argparse.BooleanOptionalAction, help="Disable the color and bold text output to be the default console font")

    args = parser.parse_args()
    
    # Setup Step setting up colors in the Terminal
    if args.disable_color:
        redtext = ''
        purpletext = ''
        yellowtext = ''
        boldtext = ''
        resetfont = ''
    else:
        redtext = '\033[31m'
        purpletext = '\033[35m'
        yellowtext = '\033[33m'
        boldtext = '\033[1m'
        resetfont = '\033[m'
        
    # Step 1: get the external interface for the called vyper contract
    # this is the "correct" interface of the called contract
    cmd_output = subprocess.run(["vyper", "-f", "external_interface", args.called_contract_path], capture_output=True, text = True)

    # If the vyper compiler indicates an error during compilation, quit
    if (not cmd_output.stdout or cmd_output.stdout.find("Error") >= 0) and cmd_output.stderr:
        print("== Error found while using vyper to extract correct external interface. Quitting! ==")
        print(cmd_output.stderr)
        return

    # Step 2: Get the interface that is defined in the caller contract
    # This is the implementation of the interface, which may be wrong
    interface_def = 'interface ' + args.interface_name + ':'

    # Open the file and read its content
    with open(args.caller_contract_path, 'r', encoding="utf-8") as file:
        file_content = file.read()

    # Cut all text before the interface definition in the contract code
    contract_interface_and_beyond = file_content[file_content.find(interface_def):]

    if contract_interface_and_beyond.find(interface_def) < 0:
        print("Cannot find this interface name. Typo?")
        return

    # Loop through the caller contract to split the interface definitions from the rest of the contract text
    lastline = ""
    multiline = False
    for line in contract_interface_and_beyond.splitlines():
        # Skip lines with interface definition, lines that define a function in the interface, lines that are comments, or empty lines
        if line.find(interface_def) > -1 or line.find('def') > -1 or line.strip().find("#") == 0 or not line.strip() or multiline:
            if multiline and line.find('->') > -1:
                multiline = False
            lastline = line
            continue
        else:
            # Consider the case of multiline function definitions in the interface
            if lastline.find('def') > -1 and lastline.find('->') < 0:
                multiline = True
            else:
                endline = line
                break

    caller_interface_definition = contract_interface_and_beyond[:contract_interface_and_beyond.find(endline)]
    rest_of_caller_code = contract_interface_and_beyond[contract_interface_and_beyond.find(endline):]

    # Step 3: Clean up and sort both lists of function definitions
    caller_contract_interface_definition = remove_unwanted_lines_and_sort(caller_interface_definition)
    called_contract_interface_definition = remove_unwanted_lines_and_sort(cmd_output.stdout)

    # Remove custom variable names from function args to allow for more simple comparison
    caller_contract_interface_definition = remove_custom_variable_names(caller_contract_interface_definition)
    called_contract_interface_definition = remove_custom_variable_names(called_contract_interface_definition)

    # Step 4: Every interface in the caller contract MUST exist in the called contract, otherwise there is a problematic mismatch
    # Loop through the interfaces in the caller contract and try to find the interface in the called contract
    for line in caller_contract_interface_definition.splitlines():
        if called_contract_interface_definition.find(line) < 0:
            # A common reason this case is reached is that the function argument name is different, so remove the first variable name
            # Another common reason this is reached is if the function argument is optional
            partial_line = line[:line.find("(")+1]
            if called_contract_interface_definition.find(partial_line) < 0:
                print(redtext+"PROBLEM LINE FOUND!",resetfont)
                print(purpletext+"Interface '" + args.interface_name + "' in " + args.caller_contract_path + " doesn't match " + args.called_contract_path,resetfont)
                print(boldtext+line,resetfont)
            else:
                # variables like ERC20 and address are generally the same, but this tool isn't smart enough to realize this
                # this code branch can also be reached if there is an annotation misalignment between nonpayable and view
                # any mismatch raises an alert even if it is a false positive, unless the strict flag is set
                if not args.strict:
                    print("likely a false positive, but check this interface definition in " + args.caller_contract_path + ":")
                    print(boldtext+line,resetfont)

    # Step 5: Every interface in the caller contract SHOULD be used later in the caller contract, otherwise it is unused and can be removed
    # If there is an unused interface in the caller contract, alert the user of the issue unless the skip_unused flag is set
    if not args.skip_unused:
        for line in caller_contract_interface_definition.splitlines():
            function_name = line[line.find("def ")+len("def "):line.find("(")]
            if rest_of_caller_code.find("." + function_name + "(") < 0:
                print()
                print(redtext+"PROBLEM LINE FOUND!",resetfont)
                print(yellowtext+"Function '" + function_name + "' in interface " + args.interface_name + " and contract " + args.caller_contract_path + " is never used",resetfont)
                print(boldtext+line,resetfont)

    if not args.strict:
        print("DONE")

if __name__ == "__main__":
    compare_interfaces()
