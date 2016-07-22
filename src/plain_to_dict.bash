#!/usr/bin/env bash

number=0
quotes=1

fmt() {
  if [[ $2 -eq $quotes ]]; then
    python -c "print('{:>16s}'.format(str('\'$1\'')))"
  else
    python -c "print('{:>16s}'.format(str('$1')))"
  fi
}

foo() {
  cat << __EOF 
  'ticker' : $(fmt $1 quotes),
  'shares' : $(fmt $2 number),
  'cvalue' : $(fmt $3 number),
  'cbasis' : $(fmt $4 number),
  'date'   : $(fmt $5 quotes),
  'comm'   : $(fmt $6 number),
  'broker' : $(fmt $7 quotes),
__EOF
}

echo -e '[\n {'
j=0
for file in ${@-'dat/broker/*.trak'}; do
  k=0
  broker=$(gbasename -s .trak $file)
  while read line; do
    if [[ $k -gt 0 ]]; then
      [[ $j -gt 1 ]] && echo ' }, {'
      foo $line $broker
    fi
    let j++
    let k++
  done < $file
done
echo -e ' },\n]'