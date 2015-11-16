#!/usr/bin/env ruby

require 'socket'
require 'netstring'
require 'json'

SOCKET_RECV_TIMEOUT = 5

def set_socket_timeout(sock,t)
	s = Integer(t)
	u = Integer((t-s)*1_000_000)
	v = [s,u].pack("l_2")
	sock.setsockopt(Socket::SOL_SOCKET, Socket::SO_RCVTIMEO, v)
end

def rpc_send(s,args,id)
	d = Netstring.dump(JSON.generate(
		'jsonrpc' => '2.0',
		'id' => id,
		'method' => 'yeti.' + args.shift,
		'params' => args
	))
	s.send(d,0)
end

def rpc_recv(s,id)
	#get length
	len_str = ''
	while true do
		c = s.recv(1)
		break if c==':'
		len_str+=c
	end

	#get response
	d = s.recv(Integer(len_str)+1)

	#validate netstring termination
	raise 'invalid response. missed comma as terminator' if d[-1] != ','
	d = d.chomp(',')

	#parse & validate
	d = JSON.parse(d)
	raise 'invalid id' if id!=d['id']

	if d["result"]
		return d
	elsif d["error"]
		raise "json_rpc error: #{d['error']}" if d["error"]
	else
		raise "unknown error. raw response: #{d}"
	end
end

def rpc_get(host,port,args)
	id = 0
	s = TCPSocket.open(host, port)
	set_socket_timeout(s,SOCKET_RECV_TIMEOUT)
	rpc_send(s,args,id)
	rpc_recv(s,id)
end

p ARGV
response = rpc_get(ARGV.shift,ARGV.shift,ARGV)
puts JSON.pretty_generate(response)
