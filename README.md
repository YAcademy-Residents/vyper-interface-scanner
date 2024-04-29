# Vyper Interface Scanner

This tool takes 2 Vyper files and an interface name as inputs. The output indicates if any interfaces declared in the caller contract do not match the called contract implementation. The output also shows if any functions in the interface are unused.

## Example Output

This tool requires the correct Vyper compiler version to be installed. Vyper 3.10 was used for testing, which can be installed with `pip3 install vyper==0.3.10`.

The example contracts in this repository, Exchange.vy and Factory.vy, are slightly modified from the [Vyper docs examples](https://github.com/vyperlang/vyper/tree/master/examples).

```
python interface-checker.py Exchange.vy Factory.vy Exchange

PROBLEM LINE FOUND! Interface 'Exchange' in Factory.vy doesn't match Exchange.vy
    def mint(address,uint256): nonpayable
likely a false positive, but check this interface definition in Factory.vy:
    def returnOne() -> uint256: nonpayable
likely a false positive, but check this interface definition in Factory.vy:
    def token() -> ERC20: view

PROBLEM LINE FOUND! Function 'mint' in interface Exchange and contract Factory.vy is never used
    def mint(address,uint256): nonpayable

PROBLEM LINE FOUND! Function 'returnOne' in interface Exchange and contract Factory.vy is never used
    def returnOne() -> uint256: nonpayable
DONE
```

```
python interface-checker.py Factory.vy Exchange.vy Factory --strict

PROBLEM LINE FOUND! Function 'trade' in interface Factory and contract Exchange.vy is never used
    def trade(ERC20,ERC20,uint256): nonpayable
```

## Docs

This tool requires the correct Vyper compiler version to be installed. Vyper 3.10 was used for testing, which can be installed with `pip3 install vyper==0.3.10`.

```
usage: interface-checker.py [-h] [--strict | --no-strict] [--skip-unused | --no-skip-unused] [--disable-color | --no-disable-color] called_contract_path caller_contract_path interface_name

Run the script with: python interface-checker.py called_contract.vy caller_contract.vy interface_name

positional arguments:
  called_contract_path  This contract is called by the other contract. This contract holds the 'correct' implementation that the caller interface should align with
  caller_contract_path  This contract stores the interface definition that attempts to match the called contract
  interface_name        The name of the interface defined in caller_contract_path.vy

options:
  -h, --help            show this help message and exit
  --strict, --no-strict
                        Only print output when there is a confirmed issue, ignore possible false positives. Do not print DONE.
  --skip-unused, --no-skip-unused
                        Skip checking for (low priority) unused interface definitions
  --disable-color, --no-disable-color
                        Disable the color and bold text output to use the default console font
```
